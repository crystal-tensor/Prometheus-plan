package microblossom

import microblossom.modules.DistributedDual
import spinal.core._
import spinal.lib._
import spinal.lib.bus.amba4.axilite._

/** Single-clock, single-context AXI4-Lite port for the frozen phase-banked core. */
object D6PhaseAxiMap {
  val AddressWidth = 12
  val Instruction = 0x000
  val Phase = 0x004
  val Selector = 0x008
  val CorrectionClear = 0x00c
  val CorrectionEdge = 0x010
  val LatchCorrection = 0x014
  val Growable = 0x018
  val ConflictValid = 0x01c
  val ConflictNodes = 0x020
  val ConflictTouches = 0x024
  val ConflictVertices = 0x028
  val SnapshotMeta = 0x02c
  val SnapshotGeneration = 0x030
  val CorrectionBase = 0x100
  val Okay = 0
  val SlaveError = 2
}

case class D6PhaseAxiEndpoint(config: DualConfig, ioConfig: DualConfig) extends Component {
  import D6PhaseAxiMap.{Instruction => InstructionAddress, _}

  require(config.contextDepth == 1, "phase and correction state are single-context")
  require(config.phaseBanks.length == 3 && !config.hardCodeWeights)
  require(config.phaseBits <= 2 && config.correctionBits <= 65535)
  require(config.readLatency > 0 && ioConfig.instructionSpec.numBits == 32)

  val io = new Bundle {
    val axi = slave(AxiLite4(AxiLite4Config(addressWidth = AddressWidth, dataWidth = 32)))
  }
  AxiLite4SpecRenamer(io.axi)
  val dual = DistributedDual(config, ioConfig)

  val awPending = RegInit(False)
  val awAddress = Reg(UInt(AddressWidth bits)) init 0
  val wPending = RegInit(False)
  val wWord = Reg(Bits(32 bits)) init 0
  val wStrobe = Reg(Bits(4 bits)) init 0
  val waitCycles = Reg(UInt(log2Up(config.readLatency + 1) bits)) init 0
  val bValid = RegInit(False)
  val bResp = Reg(Bits(2 bits)) init 0

  // Capture addresses and data independently, then issue exactly once.
  val writeSlot = !bValid && waitCycles === 0
  io.axi.aw.ready := writeSlot && !awPending
  io.axi.w.ready := writeSlot && !wPending
  io.axi.b.valid := bValid
  io.axi.b.resp := bResp
  when(io.axi.aw.fire) {
    awAddress := io.axi.aw.addr
    awPending := True
  }
  when(io.axi.w.fire) {
    wWord := io.axi.w.data
    wStrobe := io.axi.w.strb
    wPending := True
  }
  when(io.axi.b.fire) {
    bValid := False
  }

  val submitted = Instruction(ioConfig)
  submitted := wWord
  val isRaw = awAddress === InstructionAddress
  val isPhase = awAddress === Phase
  val isSelector = awAddress === Selector
  val isClear = awAddress === CorrectionClear
  val isEdge = awAddress === CorrectionEdge
  val isLatch = awAddress === LatchCorrection
  val isCoreOp = submitted.isReset() || submitted.isFindObstacle() || submitted.isGrow() ||
    submitted.isAddDefect() || submitted.isSetBlossom() || submitted.isSetSpeed()
  val supported = wStrobe === B(15, 4 bits) && (
    (isRaw && isCoreOp) ||
      (isPhase && wWord.asUInt < config.phaseBanks.length) ||
      ((isSelector || isEdge) && wWord.asUInt < config.edgeNum) ||
      ((isClear || isLatch) && wWord === 0)
  )
  val join = writeSlot && awPending && wPending
  val issue = join && supported
  val captureObstacle = RegInit(False)
  when(join) {
    awPending := False
    wPending := False
    when(supported) {
      waitCycles := config.readLatency
      captureObstacle := isRaw && submitted.isFindObstacle()
    } otherwise {
      bValid := True
      bResp := B(SlaveError, 2 bits)
    }
  }

  val phaseId = Reg(UInt(config.phaseBits bits)) init 0
  when(issue && isPhase) {
    phaseId := wWord.asUInt.resized
  }
  dual.io.message.valid := issue && (isRaw || isPhase || isSelector)
  dual.io.message.instruction := submitted
  when(isPhase) {
    dual.io.message.instruction := B(ioConfig.instructionSpec.generateReset(), 32 bits)
  } elsewhen(isSelector) {
    dual.io.message.instruction := B(ioConfig.instructionSpec.generateLoadWeightsExternal(), 32 bits)
  }
  dual.io.message.weightUpdateEdgeIndex := wWord.asUInt.resized
  dual.io.message.weightUpdateWeight := 0
  dual.io.message.weightUpdateIsRuleSelector := issue && isSelector
  dual.io.message.phaseSelectValid := issue && isPhase
  dual.io.message.phaseId := wWord.asUInt.resized
  dual.io.correctionClear := issue && isClear
  dual.io.correctionEdgeValid := issue && isEdge
  dual.io.correctionEdgeIndex := wWord.asUInt.resized

  val growable = Reg(UInt(ioConfig.weightBits bits)) init ioConfig.LengthNone
  val conflictValid = RegInit(False)
  val conflictNodes = Reg(Bits(32 bits)) init 0
  val conflictTouches = Reg(Bits(32 bits)) init 0
  val conflictVertices = Reg(Bits(32 bits)) init 0
  def pair(left: Bits, right: Bits): Bits = right.resize(16) ## left.resize(16)
  when(waitCycles =/= 0) {
    waitCycles := waitCycles - 1
    when(waitCycles === 1) {
      when(captureObstacle) {
        val conflict = dual.io.conflict
        growable := dual.io.maxGrowable.length
        conflictValid := conflict.valid
        conflictNodes := pair(conflict.node1, conflict.node2)
        conflictTouches := pair(conflict.touch1, conflict.touch2)
        conflictVertices := pair(conflict.vertex1, conflict.vertex2)
      }
      // A successful B response fences the core command/readout, not just AW/W receipt.
      bValid := True
      bResp := B(Okay, 2 bits)
    }
  }

  val wordCount = (config.correctionBits + 31) / 32
  require(CorrectionBase + 4 * wordCount <= (1 << AddressWidth))
  val snapshot = Reg(Bits((wordCount * 32) bits)) init 0
  val snapshotCount = Reg(UInt(16 bits)) init 0
  val snapshotPhase = Reg(UInt(2 bits)) init 0
  val snapshotValid = RegInit(False)
  val snapshotGeneration = Reg(UInt(32 bits)) init 0
  when(issue && isLatch) {
    snapshot := dual.io.correctionVector.resized
    snapshotCount := dual.io.correctionFaultIdCount.resized
    snapshotPhase := phaseId.resized
    snapshotValid := True
    snapshotGeneration := snapshotGeneration + 1
  }

  val rValid = RegInit(False)
  val rResp = Reg(Bits(2 bits)) init 0
  val rData = Reg(Bits(32 bits)) init 0
  // Reads sample committed state. An incomplete write pair cannot block a read.
  // A latched R beat and the B beat have independent lifetimes.
  io.axi.ar.ready := !rValid && waitCycles === 0 && !join
  io.axi.r.valid := rValid
  io.axi.r.data := rData
  io.axi.r.resp := rResp
  when(io.axi.r.fire) {
    rValid := False
  }
  when(io.axi.ar.fire) {
    rValid := True
    rData := 0
    rResp := B(Okay, 2 bits)
    switch(io.axi.ar.addr) {
      is(Growable) { rData := growable.asBits.resized }
      is(ConflictValid) { rData := conflictValid.asBits.resized }
      is(ConflictNodes) { rData := conflictNodes }
      is(ConflictTouches) { rData := conflictTouches }
      is(ConflictVertices) { rData := conflictVertices }
      is(SnapshotMeta) {
        rData := snapshotValid.asBits ## B(0, 13 bits) ## snapshotPhase.asBits ## snapshotCount.asBits
      }
      is(SnapshotGeneration) { rData := snapshotGeneration.asBits }
      for (word <- 0 until wordCount) {
        is(CorrectionBase + 4 * word) {
          when(snapshotValid) {
            rData := snapshot(32 * word + 31 downto 32 * word)
          } otherwise {
            rResp := B(SlaveError, 2 bits)
          }
        }
      }
      default { rResp := B(SlaveError, 2 bits) }
    }
  }
}
