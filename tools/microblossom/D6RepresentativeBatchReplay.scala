package microblossom

import io.circe.Json
import io.circe.parser.parse
import java.nio.file.{Files, Paths}
import spinal.core.sim._
import spinal.core._

/** Replay accepted zero/p50/p99/maximum update batches on the full steady RTL.
  *
  * This is a functional edge-state check only.  Simulation cycles are not
  * decoder latency, FPGA timing, or deadline credit.
  */
object D6RepresentativeBatchReplay extends App {
  require(args.length == 3, "expected x_steady.json z_steady.json batch_trace.json")
  val xConfig = new DualConfig(filename = args(0), hardCodeWeights = false)
  val zConfig = new DualConfig(filename = args(1), hardCodeWeights = false)
  xConfig.sanityCheck()
  zConfig.sanityCheck()
  require(xConfig.graph.vertex_num == zConfig.graph.vertex_num, "steady vertex count differs")
  require(xConfig.graph.weighted_edges == zConfig.graph.weighted_edges, "steady hardware edges differ")
  require(xConfig.graph.virtual_vertices == zConfig.graph.virtual_vertices, "steady virtuals differ")
  require(xConfig.graph.vertex_max_growth == zConfig.graph.vertex_max_growth, "steady growth differs")

  val traceText = new String(Files.readAllBytes(Paths.get(args(2))), "UTF-8")
  val trace = parse(traceText).fold(throw _, identity)
  val rows = trace.hcursor.downField("basis_rows").as[Vector[Json]].fold(throw _, identity)
  case class Batch(name: String, updates: Vector[(Int, Int)])
  val batches = rows.flatMap { row =>
    val basis = row.hcursor.get[String]("basis").fold(throw _, identity)
    val representatives = row.hcursor
      .downField("representative_batches")
      .focus
      .flatMap(_.asObject)
      .getOrElse(throw new Exception(s"$basis representatives missing"))
    representatives.toVector.sortBy(_._1).map { case (boundary, value) =>
      val updates = value.hcursor
        .downField("updates")
        .as[Vector[Vector[Int]]]
        .fold(throw _, identity)
        .map { pair =>
          require(pair.length == 2, s"$basis/$boundary malformed update")
          (pair(0), pair(1))
        }
      Batch(s"$basis/$boundary", updates)
    }
  }
  require(batches.length == 8, s"expected eight representative batches, got ${batches.length}")
  require(batches.map(_.name).toSet == Set(
    "x/zero", "x/p50", "x/p99", "x/maximum",
    "z/zero", "z/p50", "z/p99", "z/maximum"
  ))

  val baseWeights = xConfig.graph.weighted_edges.map(_.w.toInt).toVector
  val clockDivideBy = 2
  Config.sim
    .withIVerilog
    .compile({
      val dut = MicroBlossomAxi4(xConfig, clockDivideBy = clockDivideBy)
      dut.simMakePublicSnapshot()
      dut
    })
    .doSim("d6_representative_batches") { dut =>
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
            s"${batch.name}: reset mismatch at edge $edgeIndex"
          )
        }
        val writeStart = slowCycles
        batch.updates.foreach { case (edgeIndex, weight) =>
          require(edgeIndex >= 0 && edgeIndex < baseWeights.length)
          require(weight >= 0 && weight < (1 << xConfig.weightBits))
          val word = (BigInt(weight) << 16) | BigInt(edgeIndex)
          driver.write_64(0x3000, word)
        }
        val writeEnd = slowCycles
        for (_ <- 0 until 16) { dut.slow.clockDomain.waitSampling() }
        val expected = batch.updates.toMap
        for (edgeIndex <- baseWeights.indices) {
          val observed = dut.microBlossom.microBlossom.edges(edgeIndex).register.weight.toInt
          val wanted = expected.getOrElse(edgeIndex, baseWeights(edgeIndex))
          assert(observed == wanted,
            s"${batch.name}: edge $edgeIndex observed=$observed expected=$wanted")
        }
        println(
          s"REPRESENTATIVE_BATCH_PASS name=${batch.name} updates=${batch.updates.length} " +
            s"checked_edges=${baseWeights.length} axi_write_span_slow_cycles=${writeEnd - writeStart}"
        )
      }
    }
}
