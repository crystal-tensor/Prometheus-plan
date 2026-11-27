package microblossom

import microblossom.util._
import spinal.core.sim._

/** Fast regression for the bus probes; not part of the d=6 acceptance denominator. */
object D6PhaseAxiSmoke extends App {
  def tree(leaves: Int): BinaryTree = {
    val rows = collection.mutable.ArrayBuffer.fill(leaves)(BinaryTreeNode(None, None, None))
    var left = 0
    while (left + 1 < rows.size) {
      val parent = rows.size.toLong
      rows(left).p = Some(parent)
      rows(left + 1).p = Some(parent)
      rows += BinaryTreeNode(None, Some(left.toLong), Some(left.toLong + 1))
      left += 2
    }
    BinaryTree(rows.toVector)
  }

  val edges = Seq(WeightedEdge(0, 1, 2), WeightedEdge(1, 2, 3), WeightedEdge(0, 2, 4))
  val graph = SingleGraph(
    Seq.fill(3)(Position(0, 0, 0)), 3, edges, Seq(2L),
    tree(3), tree(3), tree(6), Seq.fill(3)(10L), Seq.empty, None, None
  )
  val config = DualConfig(graph = graph, hardCodeWeights = false, minimizeBits = false)
  val banks = (0 until 3).map { phase =>
    DualPhaseBank(
      "phase-" + phase, Seq.fill(3)(true), edges.map(_.w.toInt),
      Map.empty, Seq(Seq(phase + 32, 31), Seq(1), Seq(2)), 64 + phase,
      Seq.fill(3)(true), Seq(false, false, true), Seq.fill(3)(10)
    )
  }
  config.phaseBanks = banks
  val ioConfig = DualConfig(phaseBanks = banks)
  config.sanityCheck()

  def readWhileAddressWaitsForData(dut: D6PhaseAxiEndpoint): Unit = {
    import D6PhaseAxiMap._
    val bus = dut.io.axi
    def untilReady(condition: => Boolean): Unit = {
      var accepted = false
      for (_ <- 0 until 16 if !accepted) {
        sleep(1)
        accepted = condition
        dut.clockDomain.waitSampling()
        sleep(1)
      }
      assert(accepted, "incomplete AW/W pair blocked an independent read")
    }

    bus.aw.addr #= Phase
    bus.aw.valid #= true
    untilReady(bus.aw.ready.toBoolean)
    bus.aw.valid #= false
    // The manager has not sent W and need not send it to read committed state.
    bus.ar.addr #= SnapshotMeta
    bus.ar.valid #= true
    untilReady(bus.ar.ready.toBoolean)
    bus.ar.valid #= false
    bus.r.ready #= true
    untilReady {
      assert(!bus.b.valid.toBoolean, "incomplete write unexpectedly responded")
      bus.r.valid.toBoolean && bus.r.data.toLong == 0L && bus.r.resp.toInt == Okay
    }
    bus.r.ready #= false

    bus.w.data #= 0
    bus.w.strb #= 15
    bus.w.valid #= true
    untilReady(bus.w.ready.toBoolean)
    bus.w.valid #= false
    bus.b.ready #= true
    untilReady(bus.b.valid.toBoolean && bus.b.resp.toInt == Okay)
    bus.b.ready #= false
    println("AXI_PHASE_SMOKE_PARTIAL_WRITE_READ_PASS")
  }

  SimConfig.withConfig(Config.spinal()).withIVerilog.compile(D6PhaseAxiEndpoint(config, ioConfig))
    .doSim("smoke") { dut =>
      val bus = new D6PhaseAxiDriver(dut)
      dut.clockDomain.forkStimulus(period = 10)
      dut.clockDomain.waitSampling(12)
      sleep(1)
      readWhileAddressWaitsForData(dut)
      bus.execute(ioConfig.instructionSpec.generateReset())
      bus.directedProbes()
      bus.selectPhase(0)
      bus.execute(ioConfig.instructionSpec.generateAddDefect(0, 0))
      assert(bus.findObstacle(100)._2.valid)
      bus.clearCorrection()
      bus.accumulate(0)
      assert(bus.correctionRead() == ((64, "180000000")), "unsigned 32-bit read or little-endian packing failed")
      bus.report()
    }
}
