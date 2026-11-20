package microblossom

import io.circe.Json
import io.circe.parser.parse
import java.nio.file.{Files, Paths}
import scala.collection.mutable.ArrayBuffer
import spinal.core.sim._
import spinal.core._

/** Replay accepted zero/p50/p99/maximum batches through the resident rule
  * selector on the full d=6 steady RTL.
  *
  * The selected source edges are the commands. Every batch is reset first and
  * every dynamic edge register is compared with the frozen expected state.
  * Simulation cycle spans are functional interface evidence only; they are not
  * FPGA Fmax, timing closure, resource, or one-microsecond deadline credit.
  */
object D6ResidentRuleSelectorReplay extends App {
  require(args.length == 3, "expected x_steady.json z_steady.json batch_trace.json")

  def readJson(path: String): Json = {
    val text = new String(Files.readAllBytes(Paths.get(path)), "UTF-8")
    parse(text).fold(throw _, identity)
  }

  def residentRules(path: String): Map[Int, Seq[(Int, Int)]] = {
    val image = readJson(path)
    val correlations = image.hcursor
      .downField("qec_image_metadata")
      .downField("correlation_rules")
      .as[Vector[Json]]
      .fold(throw _, identity)
    val byTarget = scala.collection.mutable.Map.empty[Int, ArrayBuffer[(Int, Int)]]
    correlations.foreach { correlation =>
      val sourceEdgeIndex = correlation.hcursor.get[Int]("source_edge_index").fold(throw _, identity)
      val targets = correlation.hcursor.downField("targets").as[Vector[Json]].fold(throw _, identity)
      targets.foreach { target =>
        val lowersBase = target.hcursor.get[Boolean]("lowers_base").fold(throw _, identity)
        val replacementEven =
          target.hcursor.get[Int]("replacement_even_weight").fold(throw _, identity)
        val replacementHalf =
          target.hcursor.get[Int]("replacement_half_weight").fold(throw _, identity)
        val replacementHardware =
          target.hcursor.get[Int]("replacement_hardware_weight").fold(throw _, identity)
        require(replacementEven % 2 == 0, "resident rule has odd accepted-even weight")
        require(replacementEven / 2 == replacementHalf, "resident rule half-weight mismatch")
        require(replacementHalf == replacementHardware, "resident rule hardware-weight mismatch")
        if (lowersBase) {
          val targetEdgeIndex =
            target.hcursor.get[Int]("target_edge_index").fold(throw _, identity)
          byTarget.getOrElseUpdate(targetEdgeIndex, ArrayBuffer.empty) +=
            ((sourceEdgeIndex, replacementHardware))
        }
      }
    }
    val result = byTarget.toSeq.map { case (targetEdgeIndex, rules) =>
      require(
        rules.map(_._1).distinct.length == rules.length,
        s"target edge ${targetEdgeIndex} has duplicate source rules"
      )
      targetEdgeIndex -> rules.toVector.sortBy(_._1)
    }.toMap
    require(result.values.map(_.length).sum == 15606, "unexpected active resident-rule count")
    result
  }

  val xConfig = new DualConfig(filename = args(0), hardCodeWeights = false)
  val zConfig = new DualConfig(filename = args(1), hardCodeWeights = false)
  xConfig.sanityCheck()
  zConfig.sanityCheck()
  require(xConfig.graph.vertex_num == zConfig.graph.vertex_num, "steady vertex count differs")
  require(xConfig.graph.weighted_edges == zConfig.graph.weighted_edges, "steady hardware edges differ")
  require(xConfig.graph.virtual_vertices == zConfig.graph.virtual_vertices, "steady virtuals differ")
  require(xConfig.graph.vertex_max_growth == zConfig.graph.vertex_max_growth, "steady growth differs")

  val xRules = residentRules(args(0))
  val zRules = residentRules(args(1))
  require(xRules == zRules, "X/Z steady resident rule tables differ")
  xConfig.residentWeightRules = xRules

  case class Batch(
      name: String,
      selectedEdgeIndices: Vector[Int],
      updates: Vector[(Int, Int)]
  )
  val trace = readJson(args(2))
  val rows = trace.hcursor.downField("basis_rows").as[Vector[Json]].fold(throw _, identity)
  val batches = rows.flatMap { row =>
    val basis = row.hcursor.get[String]("basis").fold(throw _, identity)
    val representatives = row.hcursor
      .downField("representative_batches")
      .focus
      .flatMap(_.asObject)
      .getOrElse(throw new Exception(s"${basis} representatives missing"))
    representatives.toVector.sortBy(_._1).map { case (boundary, value) =>
      val phase = value.hcursor.get[String]("phase").fold(throw _, identity)
      require(phase == "steady", s"${basis}/${boundary} is not a steady batch")
      val selected = value.hcursor
        .downField("selected_edge_indices")
        .as[Vector[Int]]
        .fold(throw _, identity)
      val updates = value.hcursor
        .downField("updates")
        .as[Vector[Vector[Int]]]
        .fold(throw _, identity)
        .map { pair =>
          require(pair.length == 2, s"${basis}/${boundary} malformed update")
          (pair(0), pair(1))
        }
      Batch(s"${basis}/${boundary}", selected, updates)
    }
  }
  require(batches.length == 8, s"expected eight representative batches, got ${batches.length}")
  require(
    batches.map(_.name).toSet == Set(
      "x/zero", "x/p50", "x/p99", "x/maximum",
      "z/zero", "z/p50", "z/p99", "z/maximum"
    )
  )

  val baseWeights = xConfig.graph.weighted_edges.map(_.w.toInt).toVector
  val rulesBySource = xRules.toVector
    .flatMap { case (targetEdgeIndex, rules) =>
      rules.map { case (sourceEdgeIndex, replacementWeight) =>
        sourceEdgeIndex -> (targetEdgeIndex, replacementWeight)
      }
    }
    .groupBy(_._1)
    .map { case (sourceEdgeIndex, entries) =>
      sourceEdgeIndex -> entries.map(_._2)
    }
  batches.foreach { batch =>
    val reconstructed = baseWeights.toArray
    batch.selectedEdgeIndices.foreach { sourceEdgeIndex =>
      require(sourceEdgeIndex >= 0 && sourceEdgeIndex < baseWeights.length)
      rulesBySource.getOrElse(sourceEdgeIndex, Seq.empty).foreach {
        case (targetEdgeIndex, replacementWeight) =>
          reconstructed(targetEdgeIndex) = math.min(reconstructed(targetEdgeIndex), replacementWeight)
      }
    }
    val reconstructedUpdates = reconstructed.indices
      .filter(edgeIndex => reconstructed(edgeIndex) != baseWeights(edgeIndex))
      .map(edgeIndex => edgeIndex -> reconstructed(edgeIndex))
      .toMap
    require(
      reconstructedUpdates == batch.updates.toMap,
      s"${batch.name}: selected-source software reconstruction differs from frozen updates"
    )
  }

  val clockDivideBy = 2
  Config.sim
    .withIVerilog
    .compile({
      val dut = MicroBlossomAxi4(xConfig, clockDivideBy = clockDivideBy)
      dut.simMakePublicSnapshot()
      dut
    })
    .doSim("d6_resident_rule_selector_batches") { dut =>
      dut.clockDomain.forkStimulus(period = 10)
      dut.slow.clockDomain.forkStimulus(period = 10 * clockDivideBy)
      var slowCycles = 0L
      dut.slow.clockDomain.onActiveEdges { slowCycles += 1 }
      val driver = dut.getSimDriver()
      for (_ <- 0 until 12) { dut.slow.clockDomain.waitSampling() }
      batches.foreach { batch =>
        driver.write_64(0x1000, BigInt(DualConfig().instructionSpec.generateReset()))
        for (_ <- 0 until 16) { dut.slow.clockDomain.waitSampling() }
        for (edgeIndex <- baseWeights.indices) {
          assert(
            dut.microBlossom.microBlossom.edges(edgeIndex).register.weight.toInt == baseWeights(edgeIndex),
            s"${batch.name}: reset mismatch at edge ${edgeIndex}"
          )
        }
        val writeStart = slowCycles
        batch.selectedEdgeIndices.foreach { sourceEdgeIndex =>
          driver.write_64(0x4000, BigInt(sourceEdgeIndex))
        }
        val writeEnd = slowCycles
        for (_ <- 0 until 16) { dut.slow.clockDomain.waitSampling() }
        val expected = batch.updates.toMap
        for (edgeIndex <- baseWeights.indices) {
          val observed = dut.microBlossom.microBlossom.edges(edgeIndex).register.weight.toInt
          val wanted = expected.getOrElse(edgeIndex, baseWeights(edgeIndex))
          assert(
            observed == wanted,
            s"${batch.name}: edge ${edgeIndex} observed=${observed} expected=${wanted}"
          )
        }
        println(
          s"RESIDENT_SELECTOR_BATCH_PASS name=${batch.name} " +
            s"selectors=${batch.selectedEdgeIndices.length} updates=${batch.updates.length} " +
            s"checked_edges=${baseWeights.length} axi_write_span_slow_cycles=${writeEnd - writeStart}"
        )
      }
    }
}

