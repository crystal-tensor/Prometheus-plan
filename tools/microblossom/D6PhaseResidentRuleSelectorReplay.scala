package microblossom

import io.circe.Json
import io.circe.parser.parse
import java.nio.file.{Files, Paths}
import scala.collection.mutable.ArrayBuffer
import spinal.core.sim._
import spinal.core._

/** Replay one X/Z opening/closing phase through its full resident-selector RTL.
  *
  * Arguments: image.json phase_trace.json basis phase
  */
object D6PhaseResidentRuleSelectorReplay extends App {
  require(args.length == 4, "expected image.json phase_trace.json basis phase")
  val imagePath = args(0)
  val tracePath = args(1)
  val wantedBasis = args(2)
  val wantedPhase = args(3)
  require(Set("x", "z").contains(wantedBasis), "basis must be x or z")
  require(Set("opening", "closing").contains(wantedPhase), "phase must be opening or closing")

  def readJson(path: String): Json = {
    val text = new String(Files.readAllBytes(Paths.get(path)), "UTF-8")
    parse(text).fold(throw _, identity)
  }

  val image = readJson(imagePath)
  val metadata = image.hcursor.downField("qec_image_metadata")
  require(metadata.get[String]("basis").fold(throw _, identity) == wantedBasis)
  require(metadata.get[String]("phase").fold(throw _, identity) == wantedPhase)
  val declaredActiveRules =
    metadata.get[Int]("active_lowering_rules").fold(throw _, identity)
  val correlations = metadata
    .downField("correlation_rules")
    .as[Vector[Json]]
    .fold(throw _, identity)
  val byTarget = scala.collection.mutable.Map.empty[Int, ArrayBuffer[(Int, Int)]]
  correlations.foreach { correlation =>
    val sourceEdgeIndex =
      correlation.hcursor.get[Int]("source_edge_index").fold(throw _, identity)
    val targets = correlation.hcursor
      .downField("targets")
      .as[Vector[Json]]
      .fold(throw _, identity)
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
  val residentRules = byTarget.toSeq.map { case (targetEdgeIndex, rules) =>
    require(
      rules.map(_._1).distinct.length == rules.length,
      s"target edge ${targetEdgeIndex} has duplicate source rules"
    )
    targetEdgeIndex -> rules.toVector.sortBy(_._1)
  }.toMap
  require(
    residentRules.values.map(_.length).sum == declaredActiveRules,
    "active resident-rule count differs from image metadata"
  )

  val config = new DualConfig(filename = imagePath, hardCodeWeights = false)
  config.sanityCheck()
  config.residentWeightRules = residentRules
  val baseWeights = config.graph.weighted_edges.map(_.w.toInt).toVector

  val trace = readJson(tracePath)
  val row = trace.hcursor
    .downField("basis_rows")
    .as[Vector[Json]]
    .fold(throw _, identity)
    .find(_.hcursor.get[String]("basis").toOption.contains(wantedBasis))
    .getOrElse(throw new Exception(s"trace basis ${wantedBasis} missing"))
  val phaseRow = row.hcursor
    .downField("phases")
    .as[Vector[Json]]
    .fold(throw _, identity)
    .find(_.hcursor.get[String]("phase").toOption.contains(wantedPhase))
    .getOrElse(throw new Exception(s"trace phase ${wantedBasis}/${wantedPhase} missing"))
  val representatives = phaseRow.hcursor
    .downField("representative_batches")
    .focus
    .flatMap(_.asObject)
    .getOrElse(throw new Exception("representative batches missing"))

  case class Batch(
      boundary: String,
      selectedEdgeIndices: Vector[Int],
      updates: Vector[(Int, Int)]
  )
  val batches = representatives.toVector.sortBy(_._1).map { case (boundary, value) =>
    val selected = value.hcursor
      .downField("selected_edge_indices")
      .as[Vector[Int]]
      .fold(throw _, identity)
    val updates = value.hcursor
      .downField("updates")
      .as[Vector[Vector[Int]]]
      .fold(throw _, identity)
      .map { pair =>
        require(pair.length == 2, s"${boundary}: malformed update")
        (pair(0), pair(1))
      }
    Batch(boundary, selected, updates)
  }
  require(batches.map(_.boundary).toSet == Set("zero", "p50", "p99", "maximum"))

  val rulesBySource = residentRules.toVector
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
          reconstructed(targetEdgeIndex) =
            math.min(reconstructed(targetEdgeIndex), replacementWeight)
      }
    }
    val reconstructedUpdates = reconstructed.indices
      .filter(edgeIndex => reconstructed(edgeIndex) != baseWeights(edgeIndex))
      .map(edgeIndex => edgeIndex -> reconstructed(edgeIndex))
      .toMap
    require(
      reconstructedUpdates == batch.updates.toMap,
      s"${wantedBasis}/${wantedPhase}/${batch.boundary}: software reconstruction mismatch"
    )
  }

  val clockDivideBy = 2
  Config.sim
    .withIVerilog
    .compile({
      val dut = MicroBlossomAxi4(config, clockDivideBy = clockDivideBy)
      dut.simMakePublicSnapshot()
      dut
    })
    .doSim(s"d6_${wantedBasis}_${wantedPhase}_resident_selector") { dut =>
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
            dut.microBlossom.microBlossom.edges(edgeIndex).register.weight.toInt ==
              baseWeights(edgeIndex),
            s"${wantedBasis}/${wantedPhase}/${batch.boundary}: reset mismatch at edge ${edgeIndex}"
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
          val observed =
            dut.microBlossom.microBlossom.edges(edgeIndex).register.weight.toInt
          val wanted = expected.getOrElse(edgeIndex, baseWeights(edgeIndex))
          assert(
            observed == wanted,
            s"${wantedBasis}/${wantedPhase}/${batch.boundary}: edge ${edgeIndex} " +
              s"observed=${observed} expected=${wanted}"
          )
        }
        println(
          s"PHASE_SELECTOR_BATCH_PASS basis=${wantedBasis} phase=${wantedPhase} " +
            s"boundary=${batch.boundary} selectors=${batch.selectedEdgeIndices.length} " +
            s"updates=${batch.updates.length} checked_edges=${baseWeights.length} " +
            s"axi_write_span_slow_cycles=${writeEnd - writeStart}"
        )
      }
    }
}
