package microblossom

import io.circe.Json
import io.circe.parser.parse
import java.nio.file.{Files, Path, Paths}
import scala.collection.mutable.ArrayBuffer
import spinal.core._
import spinal.core.sim._
import microblossom.modules.DistributedDual
import microblossom.util._

case class D6FaultOutputPhase(
    name: String,
    edgeActive: Vector[Boolean],
    baseWeights: Vector[Int],
    edgeFaultIds: Vector[Vector[Int]],
    faultIdCount: Int,
    vertexActive: Vector[Boolean],
    vertexVirtual: Vector[Boolean],
    vertexMaxGrowth: Vector[Int],
    rulesByTarget: Map[Int, Vector[(Int, Int)]]
)

/** Replay complete reference correction subgraphs through the real
  * DistributedDual phase-banked sparse fault-output accumulator.
  *
  * This proves the output-map/readout slice, not that DistributedDual chose
  * the supplied subgraph. Arguments: phase_superset_plan.json correction_trace.json
  */
object D6XPhaseSupersetFaultOutputReplay extends App {
  require(args.length == 2, "expected superset plan and correction trace")

  def readJson(path: Path): Json = {
    val text = new String(Files.readAllBytes(path), "UTF-8")
    parse(text).fold(throw _, identity)
  }

  def intVector(value: Json, field: String): Vector[Int] =
    value.hcursor.downField(field).as[Vector[Int]].fold(throw _, identity)

  def nestedIntVector(value: Json, field: String): Vector[Vector[Int]] =
    value.hcursor.downField(field).as[Vector[Vector[Int]]].fold(throw _, identity)

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
    val localFaultIds = nestedIntVector(row, "fault_ids_local_edge_order")
    val faultIdCount = row.hcursor.get[Int]("fault_id_count").fold(throw _, identity)
    val localGrowth = intVector(row, "vertex_max_growth_local_order")
    require(localToEdge.length == localWeights.length)
    require(localToEdge.length == localFaultIds.length)
    require(localToVertex.length == localGrowth.length)

    val edgeActiveSet = localToEdge.toSet
    val edgeActive = Vector.tabulate(edgeNum)(edgeActiveSet.contains)
    val baseWeights = Array.fill(edgeNum)(0)
    val edgeFaultIds = Array.fill(edgeNum)(Vector.empty[Int])
    localToEdge.zip(localWeights).foreach { case (superset, weight) => baseWeights(superset) = weight }
    localToEdge.zip(localFaultIds).foreach { case (superset, ids) => edgeFaultIds(superset) = ids }
    val vertexActiveSet = localToVertex.toSet
    val vertexActive = Vector.tabulate(vertexNum)(vertexActiveSet.contains)
    val growth = Array.fill(vertexNum)(0)
    localToVertex.zip(localGrowth).foreach { case (superset, value) => growth(superset) = value }

    val sourceImagePath = workspaceRoot.resolve(row.hcursor.get[String]("source_image").fold(throw _, identity))
    val sourceImage = readJson(sourceImagePath)
    val virtualLocal = sourceImage.hcursor.downField("virtual_vertices").as[Vector[Int]].fold(throw _, identity)
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

    D6FaultOutputPhase(
      name,
      edgeActive,
      baseWeights.toVector,
      edgeFaultIds.toVector,
      faultIdCount,
      vertexActive,
      vertexVirtual,
      growth.toVector,
      rules
    )
  }

  val positions = supersetVertices.zipWithIndex.map { case (key, index) =>
    val numeric = key.drop(1).flatMap(_.asNumber.map(_.toDouble))
    Position(numeric.lift(0).getOrElse(index.toDouble), numeric.lift(1).getOrElse(0.0), numeric.lift(2).getOrElse(0.0))
  }
  val weightedEdges = supersetEdges.zipWithIndex.map { case (edge, edgeIndex) =>
    val left = edge.hcursor.get[Int]("left_vertex").fold(throw _, identity)
    val right = edge.hcursor.get[Int]("right_vertex").fold(throw _, identity)
    val available = phases.map(_.baseWeights(edgeIndex)).filter(_ > 0)
    require(available.nonEmpty, s"superset edge $edgeIndex has no phase weight")
    WeightedEdge(left, right, available.head)
  }
  val graph = SingleGraph(
    positions = positions,
    vertex_num = vertexNum,
    weighted_edges = weightedEdges,
    virtual_vertices = Vector.range(0, vertexNum).filter(index => phases.exists(_.vertexVirtual(index))).map(_.toLong),
    vertex_binary_tree = balancedTree(vertexNum),
    edge_binary_tree = balancedTree(edgeNum),
    vertex_edge_binary_tree = balancedTree(vertexNum + edgeNum),
    vertex_max_growth = Vector.tabulate(vertexNum)(index => phases.map(_.vertexMaxGrowth(index)).max.toLong),
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
      phase.edgeFaultIds,
      phase.faultIdCount,
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

  case class CorrectionBatch(
      phaseIndex: Int,
      phase: String,
      boundary: String,
      selectedEdges: Vector[Int],
      nonzeroFaultIds: Vector[Int],
      faultIdCount: Int
  )
  val trace = readJson(Paths.get(args(1)))
  val correctionRows = trace.hcursor
    .downField("representative_corrections")
    .as[Vector[Json]]
    .fold(throw _, identity)
  val batches = correctionRows.map { row =>
    val phase = row.hcursor.get[String]("phase").fold(throw _, identity)
    CorrectionBatch(
      orderedNames.indexOf(phase),
      phase,
      row.hcursor.get[String]("boundary").fold(throw _, identity),
      intVector(row, "selected_superset_edges"),
      intVector(row, "nonzero_fault_ids"),
      row.hcursor.get[Int]("fault_id_count").fold(throw _, identity)
    )
  }
  require(batches.length == 12)

  def bitsOf(ids: Seq[Int]): BigInt = ids.foldLeft(BigInt(0))((value, id) => value.setBit(id))

  Config.sim.withIVerilog
    .compile(DistributedDual(config, ioConfig))
    .doSim("d6_x_phase_superset_fault_output") { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.io.message.valid #= false
      dut.io.message.instruction #= 0
      dut.io.message.weightUpdateEdgeIndex #= 0
      dut.io.message.weightUpdateWeight #= 0
      dut.io.message.weightUpdateIsRuleSelector #= false
      dut.io.message.phaseSelectValid #= false
      dut.io.message.phaseId #= 0
      dut.io.correctionClear #= false
      dut.io.correctionEdgeValid #= false
      dut.io.correctionEdgeIndex #= 0
      for (_ <- 0 until 4) dut.clockDomain.waitSampling()

      var mapChecks = 0
      var inactiveChecks = 0
      phases.zipWithIndex.foreach { case (phase, phaseIndex) =>
        dut.simSelectPhase(phaseIndex)
        assert(dut.io.correctionFaultIdCount.toInt == phase.faultIdCount)
        for (edgeIndex <- 0 until edgeNum) {
          dut.simClearCorrection()
          dut.simAccumulateCorrectionEdge(edgeIndex)
          assert(
            dut.io.correctionVector.toBigInt == bitsOf(phase.edgeFaultIds(edgeIndex)),
            s"${phase.name}: edge $edgeIndex fault map mismatch"
          )
          mapChecks += 1
          inactiveChecks += (!phase.edgeActive(edgeIndex)).toInt
        }
      }

      var selectedEdges = 0
      batches.foreach { batch =>
        dut.simSelectPhase(batch.phaseIndex)
        assert(dut.io.correctionFaultIdCount.toInt == batch.faultIdCount)
        batch.selectedEdges.foreach(dut.simAccumulateCorrectionEdge)
        val expected = bitsOf(batch.nonzeroFaultIds)
        assert(
          dut.io.correctionVector.toBigInt == expected,
          s"${batch.phase}/${batch.boundary}: complete correction mismatch"
        )
        selectedEdges += batch.selectedEdges.length
        println(
          s"PHASE_FAULT_OUTPUT_BATCH_PASS phase=${batch.phase} boundary=${batch.boundary} " +
            s"selected_edges=${batch.selectedEdges.length} correction_bits=${batch.faultIdCount} " +
            s"nonzero_bits=${batch.nonzeroFaultIds.length}"
        )
      }
      println(
        s"PHASE_FAULT_OUTPUT_REPLAY_PASS phase_selections=${phases.length + batches.length} " +
          s"map_checks=$mapChecks inactive_empty_checks=$inactiveChecks " +
          s"complete_corrections=${batches.length} selected_edges=$selectedEdges"
      )
    }
}
