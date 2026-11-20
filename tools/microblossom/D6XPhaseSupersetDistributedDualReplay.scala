package microblossom

import io.circe.Json
import io.circe.parser.parse
import java.nio.file.{Files, Path, Paths}
import scala.collection.mutable.ArrayBuffer
import spinal.core._
import spinal.core.sim._
import microblossom.modules.DistributedDual
import microblossom.util._

case class D6DistributedPhasePlan(
    name: String,
    localToEdge: Vector[Int],
    localToVertex: Vector[Int],
    edgeActive: Vector[Boolean],
    baseWeights: Vector[Int],
    vertexActive: Vector[Boolean],
    vertexVirtual: Vector[Boolean],
    vertexMaxGrowth: Vector[Int],
    rulesByTarget: Map[Int, Vector[(Int, Int)]]
)

/** Full-superset phase replay through the real Micro Blossom DistributedDual.
  *
  * This uses phase-aware Edge and Vertex state, active masks, tightness,
  * max-growable, conflict convergecast, and resident selector logic. It does
  * not yet implement the phase-banked fault/output map or compare complete
  * corrections.
  *
  * Arguments: phase_superset_plan.json phase_trace.json steady_trace.json
  */
object D6XPhaseSupersetDistributedDualReplay extends App {
  require(args.length == 3, "expected superset plan, phase trace, steady trace")

  def readJson(path: Path): Json = {
    val text = new String(Files.readAllBytes(path), "UTF-8")
    parse(text).fold(throw _, identity)
  }

  def intVector(value: Json, field: String): Vector[Int] =
    value.hcursor.downField(field).as[Vector[Int]].fold(throw _, identity)

  def balancedTree(leaves: Int): BinaryTree = {
    require(leaves > 0)
    val nodes = ArrayBuffer.tabulate(leaves)(_ => BinaryTreeNode(None, None, None))
    var frontier = Vector.range(0, leaves)
    while (frontier.length > 1) {
      val next = ArrayBuffer[Int]()
      var index = 0
      while (index < frontier.length) {
        if (index + 1 == frontier.length) {
          next += frontier(index)
          index += 1
        } else {
          val left = frontier(index)
          val right = frontier(index + 1)
          val parent = nodes.length
          nodes += BinaryTreeNode(None, Some(left), Some(right))
          nodes(left).p = Some(parent)
          nodes(right).p = Some(parent)
          next += parent
          index += 2
        }
      }
      frontier = next.toVector
    }
    BinaryTree(nodes.toVector)
  }

  val planPath = Paths.get(args(0)).toAbsolutePath.normalize
  val workspaceRoot = planPath.getParent.getParent
  val plan = readJson(planPath)
  val xPlan = plan.hcursor
    .downField("basis_plans")
    .as[Vector[Json]]
    .fold(throw _, identity)
    .find(_.hcursor.get[String]("basis").toOption.contains("x"))
    .getOrElse(throw new Exception("X basis plan missing"))
  val supersetVertices = xPlan.hcursor
    .downField("superset_vertices")
    .as[Vector[Vector[Json]]]
    .fold(throw _, identity)
  val supersetEdges = xPlan.hcursor
    .downField("superset_edges")
    .as[Vector[Json]]
    .fold(throw _, identity)
  val edgeNum = supersetEdges.length
  val vertexNum = supersetVertices.length
  val phaseRows = xPlan.hcursor.downField("phases").as[Vector[Json]].fold(throw _, identity)
  val orderedNames = Vector("opening", "steady", "closing")

  val phases = orderedNames.map { name =>
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
    val baseWeights = Array.fill(edgeNum)(0)
    localToEdge.zip(localWeights).foreach { case (superset, weight) => baseWeights(superset) = weight }
    val vertexActive = Vector.tabulate(vertexNum)(localToVertex.toSet.contains)
    val growth = Array.fill(vertexNum)(0)
    localToVertex.zip(localGrowth).foreach { case (superset, value) => growth(superset) = value }

    val sourceImagePath = workspaceRoot.resolve(
      row.hcursor.get[String]("source_image").fold(throw _, identity)
    )
    val sourceImage = readJson(sourceImagePath)
    val virtualLocal = sourceImage.hcursor
      .downField("virtual_vertices")
      .as[Vector[Int]]
      .fold(throw _, identity)
    val virtualSuperset = virtualLocal.map(localToVertex).toSet
    val vertexVirtual = Vector.tabulate(vertexNum)(virtualSuperset.contains)

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

    D6DistributedPhasePlan(
      name,
      localToEdge,
      localToVertex,
      edgeActive,
      baseWeights.toVector,
      vertexActive,
      vertexVirtual,
      growth.toVector,
      rules
    )
  }

  val positions = supersetVertices.zipWithIndex.map { case (key, index) =>
    val numeric = key.drop(1).flatMap(_.asNumber.map(_.toDouble))
    Position(
      numeric.lift(0).getOrElse(index.toDouble),
      numeric.lift(1).getOrElse(0.0),
      numeric.lift(2).getOrElse(0.0)
    )
  }
  val weightedEdges = supersetEdges.zipWithIndex.map { case (edge, edgeIndex) =>
    val left = edge.hcursor.get[Int]("left_vertex").fold(throw _, identity)
    val right = edge.hcursor.get[Int]("right_vertex").fold(throw _, identity)
    val available = phases.map(_.baseWeights(edgeIndex)).filter(_ > 0)
    require(available.nonEmpty, s"superset edge $edgeIndex has no phase weight")
    WeightedEdge(left, right, available.head)
  }
  val vertexMaxGrowth = Vector.tabulate(vertexNum) { vertexIndex =>
    phases.map(_.vertexMaxGrowth(vertexIndex)).max
  }
  val virtualUnion = Vector.range(0, vertexNum).filter { vertexIndex =>
    phases.exists(_.vertexVirtual(vertexIndex))
  }
  val graph = SingleGraph(
    positions = positions,
    vertex_num = vertexNum,
    weighted_edges = weightedEdges,
    virtual_vertices = virtualUnion.map(_.toLong),
    vertex_binary_tree = balancedTree(vertexNum),
    edge_binary_tree = balancedTree(edgeNum),
    vertex_edge_binary_tree = balancedTree(vertexNum + edgeNum),
    vertex_max_growth = vertexMaxGrowth.map(_.toLong),
    offloading = Seq.empty,
    layer_fusion = None,
    parity_reporters = None
  )

  val banks = phases.map { phase =>
    DualPhaseBank(
      phase.name,
      phase.edgeActive,
      phase.baseWeights,
      phase.rulesByTarget,
      phase.vertexActive,
      phase.vertexVirtual,
      phase.vertexMaxGrowth
    )
  }
  val config = DualConfig(graph = graph)
  config.contextDepth = 1
  config.hardCodeWeights = false
  config.supportOffloading = false
  config.supportLayerFusion = false
  config.phaseBanks = banks
  config.sanityCheck()
  val ioConfig = DualConfig(
    vertexBits = config.vertexBits,
    weightBits = config.weightBits,
    contextDepth = 1,
    phaseBanks = banks,
    minimizeBits = false
  )

  case class Batch(
      phaseIndex: Int,
      phase: String,
      boundary: String,
      selectedSupersetEdges: Vector[Int],
      expectedSupersetUpdates: Map[Int, Int]
  )

  val phaseTrace = readJson(Paths.get(args(1)))
  val steadyTrace = readJson(Paths.get(args(2)))
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
      steadyTraceX.hcursor.downField("representative_batches").focus.flatMap(_.asObject).get
    } else {
      phaseTraceX.hcursor
        .downField("phases")
        .as[Vector[Json]]
        .fold(throw _, identity)
        .find(_.hcursor.get[String]("phase").toOption.contains(phase))
        .flatMap(_.hcursor.downField("representative_batches").focus)
        .flatMap(_.asObject)
        .get
    }
  }

  val boundaries = Vector("zero", "p50", "p99", "maximum")
  val batches = phases.zipWithIndex.flatMap { case (phase, phaseIndex) =>
    val representatives = representativeObject(phase.name)
    boundaries.map { boundary =>
      val row = representatives(boundary).get
      val selectedLocal = intVector(row, "selected_edge_indices")
      val updatesLocal = row.hcursor.downField("updates").as[Vector[Vector[Int]]].fold(throw _, identity)
      Batch(
        phaseIndex,
        phase.name,
        boundary,
        selectedLocal.map(phase.localToEdge),
        updatesLocal.map(pair => phase.localToEdge(pair(0)) -> pair(1)).toMap
      )
    }
  }
  val batchByKey = batches.map(batch => (batch.phase, batch.boundary) -> batch).toMap

  Config.sim.withIVerilog
    .compile({
      val dut = DistributedDual(config, ioConfig)
      dut.simMakePublicSnapshot()
      dut.currentPhase.simPublic()
      dut
    })
    .doSim("d6_x_phase_superset_distributed_dual") { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.io.message.valid #= false
      dut.io.message.instruction #= 0
      dut.io.message.weightUpdateEdgeIndex #= 0
      dut.io.message.weightUpdateWeight #= 0
      dut.io.message.weightUpdateIsRuleSelector #= false
      dut.io.message.phaseSelectValid #= false
      dut.io.message.phaseId #= 0
      for (_ <- 0 until 4) dut.clockDomain.waitSampling()

      def checkState(phase: D6DistributedPhasePlan, updates: Map[Int, Int]): Unit = {
        for (edgeIndex <- 0 until edgeNum) {
          val active = dut.edges(edgeIndex).activeRegister.toBoolean
          val weight = dut.edges(edgeIndex).register.weight.toInt
          val expectedWeight =
            if (phase.edgeActive(edgeIndex)) updates.getOrElse(edgeIndex, phase.baseWeights(edgeIndex))
            else phase.baseWeights(edgeIndex)
          assert(active == phase.edgeActive(edgeIndex), s"${phase.name}: edge $edgeIndex active")
          assert(weight == expectedWeight, s"${phase.name}: edge $edgeIndex weight=$weight expected=$expectedWeight")
          if (!active) {
            assert(dut.edges(edgeIndex).io.maxGrowable.length.toInt == config.LengthNone)
            assert(!dut.edges(edgeIndex).io.conflict.valid.toBoolean)
          }
        }
        for (vertexIndex <- 0 until vertexNum) {
          val active = dut.vertices(vertexIndex).activeRegister.toBoolean
          assert(active == phase.vertexActive(vertexIndex), s"${phase.name}: vertex $vertexIndex active")
          if (!active) {
            assert(dut.vertices(vertexIndex).io.maxGrowable.length.toInt == config.LengthNone)
          }
        }
      }

      boundaries.foreach { boundary =>
        phases.zipWithIndex.foreach { case (phase, phaseIndex) =>
          val batch = batchByKey((phase.name, boundary))
          dut.simSelectPhase(phaseIndex)
          checkState(phase, Map.empty)
          batch.selectedSupersetEdges.foreach(dut.simApplyResidentRuleSelector)
          checkState(phase, batch.expectedSupersetUpdates)
          val (maxGrowable, conflict) = dut.simExecute(ioConfig.instructionSpec.generateFindObstacle())
          assert(maxGrowable.length == config.LengthNone, s"${phase.name}/$boundary unexpected growable")
          assert(!conflict.valid, s"${phase.name}/$boundary unexpected conflict")
          println(
            s"PHASE_DISTRIBUTED_DUAL_BATCH_PASS phase=${phase.name} boundary=$boundary " +
              s"selectors=${batch.selectedSupersetEdges.length} updates=${batch.expectedSupersetUpdates.size} " +
              s"checked_edges=$edgeNum checked_vertices=$vertexNum"
          )
        }
      }
      println(
        s"PHASE_DISTRIBUTED_DUAL_TRANSITION_PASS phase_selections=${batches.length} " +
          s"selector_commands=${batches.map(_.selectedSupersetEdges.length).sum} " +
          s"checked_edges=$edgeNum checked_vertices=$vertexNum"
      )
    }
}
