package microblossom

import io.circe.Json
import io.circe.parser.parse
import java.nio.file.{Files, Paths}
import scala.collection.mutable.ArrayBuffer
import spinal.core._
import spinal.core.sim._

case class D6PhaseBankData(
    name: String,
    edgeActive: Vector[Boolean],
    baseWeights: Vector[Int],
    vertexActive: Vector[Boolean],
    vertexMaxGrowth: Vector[Int],
    rulesByTarget: Map[Int, Vector[(Int, Int)]]
)

case class D6XPhaseSupersetEdgeBank(phases: Vector[D6PhaseBankData]) extends Component {
  require(phases.length == 3, "opening/steady/closing banks required")
  val edgeNum = phases.head.edgeActive.length
  val vertexNum = phases.head.vertexActive.length
  require(phases.forall(_.edgeActive.length == edgeNum), "edge bank size mismatch")
  require(phases.forall(_.baseWeights.length == edgeNum), "weight bank size mismatch")
  require(phases.forall(_.vertexActive.length == vertexNum), "vertex bank size mismatch")
  require(phases.forall(_.vertexMaxGrowth.length == vertexNum), "growth bank size mismatch")
  val weightBits = math.max(1, BigInt(phases.flatMap(_.baseWeights).max).bitLength)
  val growthBits = math.max(1, BigInt(phases.flatMap(_.vertexMaxGrowth).max).bitLength)
  val edgeBits = math.max(1, log2Up(edgeNum))

  phases.foreach { phase =>
    phase.rulesByTarget.foreach { case (target, rules) =>
      require(target >= 0 && target < edgeNum, s"${phase.name}: target out of range")
      require(rules.map(_._1).distinct.length == rules.length, s"${phase.name}: duplicate selector")
      rules.foreach { case (source, replacement) =>
        require(source >= 0 && source < edgeNum, s"${phase.name}: source out of range")
        require(phase.edgeActive(source), s"${phase.name}: inactive selector source")
        require(phase.edgeActive(target), s"${phase.name}: inactive selector target")
        require(replacement >= 0 && BigInt(replacement) < (BigInt(1) << weightBits))
      }
    }
  }

  val io = new Bundle {
    val phaseSelectValid = in Bool ()
    val phaseId = in UInt (2 bits)
    val selectorValid = in Bool ()
    val selectorEdge = in UInt (edgeBits bits)
    val currentPhase = out UInt (2 bits)
    val lastSelectorAccepted = out Bool ()
    val lastSelectorRejected = out Bool ()
    val rejectedSelectorCount = out UInt (32 bits)
  }

  val phaseRegister = Reg(UInt(2 bits)) init (0)
  val acceptedRegister = Reg(Bool) init (False)
  val rejectedRegister = Reg(Bool) init (False)
  val rejectedCountRegister = Reg(UInt(32 bits)) init (0)
  io.currentPhase := phaseRegister
  io.lastSelectorAccepted := acceptedRegister
  io.lastSelectorRejected := rejectedRegister
  io.rejectedSelectorCount := rejectedCountRegister

  acceptedRegister := False
  rejectedRegister := False

  val phaseEdgeMasks = phases.map { phase =>
    Vec(phase.edgeActive.map(value => if (value) True else False))
  }
  val selectorInRange = io.selectorEdge < U(edgeNum, edgeBits bits)
  val selectedSourceActive = Bool
  selectedSourceActive := False
  when(selectorInRange) {
    switch(phaseRegister) {
      phases.indices.foreach { phaseIndex =>
        is(U(phaseIndex, 2 bits)) {
          selectedSourceActive := phaseEdgeMasks(phaseIndex)(io.selectorEdge)
        }
      }
    }
  }

  val validPhaseSelect = io.phaseSelectValid && io.phaseId < U(phases.length, 2 bits)
  when(validPhaseSelect) {
    phaseRegister := io.phaseId
  } elsewhen (io.selectorValid) {
    when(selectedSourceActive) {
      acceptedRegister := True
    } otherwise {
      rejectedRegister := True
      rejectedCountRegister := rejectedCountRegister + 1
    }
  }

  val edges = phases.head.edgeActive.indices.map { edgeIndex =>
    new Area {
      val active = Reg(Bool) init (phases.head.edgeActive(edgeIndex))
      val weight = Reg(UInt(weightBits bits)) init (phases.head.baseWeights(edgeIndex))
      when(validPhaseSelect) {
        switch(io.phaseId) {
          phases.indices.foreach { phaseIndex =>
            is(U(phaseIndex, 2 bits)) {
              active := (if (phases(phaseIndex).edgeActive(edgeIndex)) True else False)
              weight := phases(phaseIndex).baseWeights(edgeIndex)
            }
          }
        }
      } elsewhen (io.selectorValid && selectedSourceActive && active) {
        val ruleHit = Bool
        val replacement = UInt(weightBits bits)
        ruleHit := False
        replacement := weight
        phases.indices.foreach { phaseIndex =>
          when(phaseRegister === U(phaseIndex, 2 bits)) {
            phases(phaseIndex).rulesByTarget.getOrElse(edgeIndex, Vector.empty).foreach {
              case (source, value) =>
                when(io.selectorEdge === U(source, edgeBits bits)) {
                  ruleHit := True
                  replacement := U(value, weightBits bits)
                }
            }
          }
        }
        when(ruleHit && replacement < weight) {
          weight := replacement
        }
      }
    }
  }

  val vertices = phases.head.vertexActive.indices.map { vertexIndex =>
    new Area {
      val active = Reg(Bool) init (phases.head.vertexActive(vertexIndex))
      val maximumGrowth = Reg(UInt(growthBits bits)) init (
        phases.head.vertexMaxGrowth(vertexIndex)
      )
      when(validPhaseSelect) {
        switch(io.phaseId) {
          phases.indices.foreach { phaseIndex =>
            is(U(phaseIndex, 2 bits)) {
              active := (if (phases(phaseIndex).vertexActive(vertexIndex)) True else False)
              maximumGrowth := phases(phaseIndex).vertexMaxGrowth(vertexIndex)
            }
          }
        }
      }
    }
  }

  def simMakePublic(): Unit = {
    phaseRegister.simPublic()
    acceptedRegister.simPublic()
    rejectedRegister.simPublic()
    rejectedCountRegister.simPublic()
    edges.foreach { edge =>
      edge.active.simPublic()
      edge.weight.simPublic()
    }
    vertices.foreach { vertex =>
      vertex.active.simPublic()
      vertex.maximumGrowth.simPublic()
    }
  }
}

/** Functional RTL replay of one X-basis phase-superset state bank.
  *
  * This verifies atomic mask/weight/rule/growth bank selection and inactive
  * selector rejection. It is not yet integrated into DistributedDual and does
  * not compare complete corrections, timing closure, or FPGA resources.
  *
  * Arguments: phase_superset_plan.json phase_trace.json steady_trace.json
  */
object D6XPhaseSupersetEdgeBankReplay extends App {
  require(args.length == 3, "expected superset plan, phase trace, steady trace")

  def readJson(path: String): Json = {
    val text = new String(Files.readAllBytes(Paths.get(path)), "UTF-8")
    parse(text).fold(throw _, identity)
  }

  def intVector(value: Json, field: String): Vector[Int] =
    value.hcursor.downField(field).as[Vector[Int]].fold(throw _, identity)

  val plan = readJson(args(0))
  val xPlan = plan.hcursor
    .downField("basis_plans")
    .as[Vector[Json]]
    .fold(throw _, identity)
    .find(_.hcursor.get[String]("basis").toOption.contains("x"))
    .getOrElse(throw new Exception("X basis plan missing"))
  val edgeNum = xPlan.hcursor.downField("superset_edges").as[Vector[Json]].fold(throw _, identity).length
  val vertexNum = xPlan.hcursor.downField("superset_vertices").as[Vector[Json]].fold(throw _, identity).length
  val phaseRows = xPlan.hcursor.downField("phases").as[Vector[Json]].fold(throw _, identity)
  val orderedNames = Vector("opening", "steady", "closing")

  case class PlanPhase(
      name: String,
      localToEdge: Vector[Int],
      localToVertex: Vector[Int],
      edgeActive: Vector[Boolean],
      baseWeights: Vector[Int],
      vertexActive: Vector[Boolean],
      vertexMaxGrowth: Vector[Int],
      rulesByTarget: Map[Int, Vector[(Int, Int)]]
  )

  val planPhases = orderedNames.map { name =>
    val row = phaseRows
      .find(_.hcursor.get[String]("phase").toOption.contains(name))
      .getOrElse(throw new Exception(s"phase $name missing"))
    val localToEdge = intVector(row, "local_to_superset_edge")
    val localToVertex = intVector(row, "local_to_superset_vertex")
    val localWeights = intVector(row, "base_weights_local_edge_order")
    val localGrowth = intVector(row, "vertex_max_growth_local_order")
    require(localToEdge.length == localWeights.length)
    require(localToVertex.length == localGrowth.length)
    val edgeActive = Vector.tabulate(edgeNum)(localToEdge.toSet.contains)
    val baseWeightsArray = Array.fill(edgeNum)(0)
    localToEdge.zip(localWeights).foreach { case (superset, weight) =>
      baseWeightsArray(superset) = weight
    }
    val vertexActive = Vector.tabulate(vertexNum)(localToVertex.toSet.contains)
    val growthArray = Array.fill(vertexNum)(0)
    localToVertex.zip(localGrowth).foreach { case (superset, growth) =>
      growthArray(superset) = growth
    }
    val rules = row.hcursor
      .downField("active_resident_rules")
      .as[Vector[Json]]
      .fold(throw _, identity)
      .map { rule =>
        val source = rule.hcursor.get[Int]("source_edge").fold(throw _, identity)
        val target = rule.hcursor.get[Int]("target_edge").fold(throw _, identity)
        val replacement = rule.hcursor.get[Int]("replacement_weight").fold(throw _, identity)
        target -> (source, replacement)
      }
      .groupBy(_._1)
      .map { case (target, values) => target -> values.map(_._2).sortBy(_._1) }
    PlanPhase(
      name,
      localToEdge,
      localToVertex,
      edgeActive,
      baseWeightsArray.toVector,
      vertexActive,
      growthArray.toVector,
      rules
    )
  }

  val hardwarePhases = planPhases.map { phase =>
    D6PhaseBankData(
      phase.name,
      phase.edgeActive,
      phase.baseWeights,
      phase.vertexActive,
      phase.vertexMaxGrowth,
      phase.rulesByTarget
    )
  }

  case class Batch(
      phaseIndex: Int,
      phase: String,
      boundary: String,
      selectedSupersetEdges: Vector[Int],
      expectedSupersetUpdates: Map[Int, Int]
  )

  val phaseTrace = readJson(args(1))
  val steadyTrace = readJson(args(2))
  val phaseTraceX = phaseTrace.hcursor
    .downField("basis_rows")
    .as[Vector[Json]]
    .fold(throw _, identity)
    .find(_.hcursor.get[String]("basis").toOption.contains("x"))
    .getOrElse(throw new Exception("X phase trace missing"))
  val steadyTraceX = steadyTrace.hcursor
    .downField("basis_rows")
    .as[Vector[Json]]
    .fold(throw _, identity)
    .find(_.hcursor.get[String]("basis").toOption.contains("x"))
    .getOrElse(throw new Exception("X steady trace missing"))

  def representativeObject(phase: String): io.circe.JsonObject = {
    if (phase == "steady") {
      steadyTraceX.hcursor
        .downField("representative_batches")
        .focus
        .flatMap(_.asObject)
        .getOrElse(throw new Exception("steady representatives missing"))
    } else {
      phaseTraceX.hcursor
        .downField("phases")
        .as[Vector[Json]]
        .fold(throw _, identity)
        .find(_.hcursor.get[String]("phase").toOption.contains(phase))
        .flatMap(_.hcursor.downField("representative_batches").focus)
        .flatMap(_.asObject)
        .getOrElse(throw new Exception(s"$phase representatives missing"))
    }
  }

  val boundaries = Vector("zero", "p50", "p99", "maximum")
  val batches = planPhases.zipWithIndex.flatMap { case (phase, phaseIndex) =>
    val representatives = representativeObject(phase.name)
    boundaries.map { boundary =>
      val row = representatives(boundary).getOrElse(throw new Exception(s"$boundary missing"))
      val selectedLocal = intVector(row, "selected_edge_indices")
      val updatesLocal = row.hcursor
        .downField("updates")
        .as[Vector[Vector[Int]]]
        .fold(throw _, identity)
      val selectedSuperset = selectedLocal.map(phase.localToEdge)
      val expectedUpdates = updatesLocal.map { pair =>
        require(pair.length == 2)
        phase.localToEdge(pair(0)) -> pair(1)
      }.toMap
      val reconstructed = phase.baseWeights.toArray
      val rulesBySource = phase.rulesByTarget.toVector
        .flatMap { case (target, rules) => rules.map { case (source, replacement) => source -> (target, replacement) } }
        .groupBy(_._1)
        .map { case (source, entries) => source -> entries.map(_._2) }
      selectedSuperset.foreach { source =>
        rulesBySource.getOrElse(source, Seq.empty).foreach { case (target, replacement) =>
          reconstructed(target) = math.min(reconstructed(target), replacement)
        }
      }
      val reconstructedUpdates = reconstructed.indices
        .filter(index => phase.edgeActive(index) && reconstructed(index) != phase.baseWeights(index))
        .map(index => index -> reconstructed(index))
        .toMap
      require(
        reconstructedUpdates == expectedUpdates,
        s"${phase.name}/$boundary: translated software reconstruction mismatch"
      )
      Batch(phaseIndex, phase.name, boundary, selectedSuperset, expectedUpdates)
    }
  }

  val phaseBatches = batches.groupBy(batch => (batch.phase, batch.boundary))
  val clockPeriod = 10
  Config.sim
    .withIVerilog
    .compile({
      val dut = D6XPhaseSupersetEdgeBank(hardwarePhases)
      dut.simMakePublic()
      dut
    })
    .doSim("d6_x_phase_superset_edge_bank") { dut =>
      dut.clockDomain.forkStimulus(period = clockPeriod)
      dut.io.phaseSelectValid #= false
      dut.io.phaseId #= 0
      dut.io.selectorValid #= false
      dut.io.selectorEdge #= 0
      for (_ <- 0 until 4) { dut.clockDomain.waitSampling() }
      var selectorCommands = 0
      var phaseSelections = 0
      var rejectedSelectors = 0

      def checkPhaseState(phase: PlanPhase, updates: Map[Int, Int]): Unit = {
        for (edgeIndex <- 0 until edgeNum) {
          val observedActive = dut.edges(edgeIndex).active.toBoolean
          val observedWeight = dut.edges(edgeIndex).weight.toInt
          val expectedActive = phase.edgeActive(edgeIndex)
          val expectedWeight =
            if (expectedActive) updates.getOrElse(edgeIndex, phase.baseWeights(edgeIndex)) else 0
          assert(observedActive == expectedActive, s"${phase.name}: edge $edgeIndex active mismatch")
          assert(
            observedWeight == expectedWeight,
            s"${phase.name}: edge $edgeIndex weight=$observedWeight expected=$expectedWeight"
          )
        }
        for (vertexIndex <- 0 until vertexNum) {
          assert(
            dut.vertices(vertexIndex).active.toBoolean == phase.vertexActive(vertexIndex),
            s"${phase.name}: vertex $vertexIndex active mismatch"
          )
          assert(
            dut.vertices(vertexIndex).maximumGrowth.toInt == phase.vertexMaxGrowth(vertexIndex),
            s"${phase.name}: vertex $vertexIndex growth mismatch"
          )
        }
      }

      def selectPhase(phaseIndex: Int): Unit = {
        dut.io.phaseId #= phaseIndex
        dut.io.phaseSelectValid #= true
        dut.clockDomain.waitSampling()
        dut.io.phaseSelectValid #= false
        dut.clockDomain.waitSampling()
        assert(dut.io.currentPhase.toInt == phaseIndex)
        phaseSelections += 1
      }

      def applySelector(source: Int): Unit = {
        dut.io.selectorEdge #= source
        dut.io.selectorValid #= true
        dut.clockDomain.waitSampling()
        sleep(1)
        assert(dut.io.lastSelectorAccepted.toBoolean, s"active selector $source rejected")
        dut.io.selectorValid #= false
        dut.clockDomain.waitSampling()
        selectorCommands += 1
      }

      def rejectInactiveSelector(phase: PlanPhase): Unit = {
        val source = phase.edgeActive.indices.find(index => !phase.edgeActive(index)).get
        val before = dut.edges.map(_.weight.toInt)
        val beforeRejected = dut.io.rejectedSelectorCount.toLong
        dut.io.selectorEdge #= source
        dut.io.selectorValid #= true
        dut.clockDomain.waitSampling()
        sleep(1)
        assert(dut.io.lastSelectorRejected.toBoolean, s"inactive selector $source accepted")
        dut.io.selectorValid #= false
        dut.clockDomain.waitSampling()
        assert(dut.io.rejectedSelectorCount.toLong == beforeRejected + 1)
        assert(dut.edges.map(_.weight.toInt) == before, s"inactive selector $source changed weight state")
        rejectedSelectors += 1
      }

      boundaries.foreach { boundary =>
        planPhases.zipWithIndex.foreach { case (phase, phaseIndex) =>
          val batch = phaseBatches((phase.name, boundary)).head
          selectPhase(phaseIndex)
          checkPhaseState(phase, Map.empty)
          batch.selectedSupersetEdges.foreach(applySelector)
          checkPhaseState(phase, batch.expectedSupersetUpdates)
          rejectInactiveSelector(phase)
          println(
            s"PHASE_SUPERSET_BATCH_PASS phase=${phase.name} boundary=$boundary " +
              s"selectors=${batch.selectedSupersetEdges.length} updates=${batch.expectedSupersetUpdates.size} " +
              s"checked_edges=$edgeNum checked_vertices=$vertexNum"
          )
        }
      }
      println(
        s"PHASE_SUPERSET_TRANSITION_PASS phase_selections=$phaseSelections " +
          s"selector_commands=$selectorCommands rejected_inactive_selectors=$rejectedSelectors " +
          s"checked_edges=$edgeNum checked_vertices=$vertexNum"
      )
    }
}
