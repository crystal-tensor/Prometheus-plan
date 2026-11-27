package microblossom

import microblossom.types.{DataConflictRaw, DataMaxGrowable}
import spinal.core.sim._

/** Test manager. The decoder's only functional command/result access is the bus. */
final class D6PhaseAxiDriver(dut: D6PhaseAxiEndpoint) {
  import D6PhaseAxiMap._

  private val bus = dut.io.axi
  private val spec = dut.ioConfig.instructionSpec
  private val cycleLimit = 64
  private var cycles, awCount, wCount, bCount, arCount, rCount = 0L
  private var addressFirst, dataFirst, simultaneous, bStallCycles, rStallCycles = 0L
  private var errorB, errorR = 0L
  private var phaseWrites, selectorWrites, xorWrites, vectors, vectorWords, obstacleReads = 0L
  private var priorB: Option[Int] = None
  private var priorR: Option[(Long, Int)] = None
  private var activePhase = 0

  bus.aw.valid #= false
  bus.aw.addr #= 0
  bus.aw.prot #= 0
  bus.w.valid #= false
  bus.w.data #= 0
  bus.w.strb #= 0
  bus.b.ready #= false
  bus.ar.valid #= false
  bus.ar.addr #= 0
  bus.ar.prot #= 0
  bus.r.ready #= false

  private case class Sample(
      awFire: Boolean, wFire: Boolean, arFire: Boolean,
      b: Option[Int], r: Option[(Long, Int)]
  )

  private def step(): Sample = {
    // Sample settled signals before the accepting edge; drive the next cycle after it.
    sleep(1)
    val sample = Sample(
      bus.aw.valid.toBoolean && bus.aw.ready.toBoolean,
      bus.w.valid.toBoolean && bus.w.ready.toBoolean,
      bus.ar.valid.toBoolean && bus.ar.ready.toBoolean,
      if (bus.b.valid.toBoolean) Some(bus.b.resp.toInt) else None,
      if (bus.r.valid.toBoolean) Some((bus.r.data.toLong & 0xffffffffL, bus.r.resp.toInt)) else None
    )
    priorB.foreach(value => assert(sample.b.contains(value), "BVALID/BRESP changed during a stall"))
    priorR.foreach(value => assert(sample.r.contains(value), "RVALID/RDATA/RRESP changed during a stall"))
    sample.b.foreach { response =>
      assert(bCount < math.min(awCount, wCount), "B response without a joined write")
      if (bus.b.ready.toBoolean) {
        bCount += 1
        if (response != Okay) errorB += 1
      } else bStallCycles += 1
    }
    sample.r.foreach { case (_, response) =>
      assert(rCount < arCount, "R response without an accepted AR")
      if (bus.r.ready.toBoolean) {
        rCount += 1
        if (response != Okay) errorR += 1
      } else rStallCycles += 1
    }
    priorB = if (bus.b.ready.toBoolean) None else sample.b
    priorR = if (bus.r.ready.toBoolean) None else sample.r
    if (sample.awFire) awCount += 1
    if (sample.wFire) wCount += 1
    if (sample.arFire) arCount += 1
    dut.clockDomain.waitSampling()
    sleep(1)
    cycles += 1
    sample
  }

  private def drivePair(addr: Int, data: Long, strobe: Int, aDelay: Int, dDelay: Int): Unit = {
    bus.aw.addr #= addr
    bus.w.data #= data
    bus.w.strb #= strobe
    var aAt, dAt = -1
    var age = 0
    while (aAt < 0 || dAt < 0) {
      assert(age < cycleLimit, s"AW/W timeout on address $addr")
      bus.aw.valid #= aAt < 0 && age >= aDelay
      bus.w.valid #= dAt < 0 && age >= dDelay
      val sample = step()
      if (sample.awFire) aAt = age
      if (sample.wFire) dAt = age
      age += 1
    }
    bus.aw.valid #= false
    bus.w.valid #= false
    if (aAt < dAt) addressFirst += 1
    else if (dAt < aAt) dataFirst += 1
    else simultaneous += 1
  }

  private def awaitB(): Int = {
    for (_ <- 0 until cycleLimit) {
      val sample = step()
      if (sample.b.nonEmpty) return sample.b.get
    }
    throw new AssertionError("B response timeout")
  }

  private def finishB(expected: Int): Unit = {
    bus.b.ready #= true
    assert(step().b.contains(expected), s"unexpected B response, expected $expected")
    bus.b.ready #= false
  }

  private def write(address: Int, data: Long, strobe: Int = 15, expected: Int = Okay): Unit = {
    val seq = awCount
    val (aDelay, dDelay) = (seq % 3).toInt match {
      case 0 => (0, 0)
      case 1 => (0, 2)
      case _ => (3, 0)
    }
    drivePair(address, data, strobe, aDelay, dDelay)
    val response = awaitB()
    assert(response == expected, s"address $address: B response $response != $expected")
    for (_ <- 0 until (seq % 4).toInt) assert(step().b.contains(response))
    finishB(response)
  }

  private def beginRead(addr: Int): (Long, Int) = {
    bus.ar.addr #= addr
    bus.ar.valid #= true
    var ar = false
    var age = 0
    while (!ar && age < cycleLimit) {
      ar = step().arFire
      age += 1
    }
    assert(ar, s"AR timeout on address $addr")
    bus.ar.valid #= false
    for (_ <- 0 until cycleLimit) {
      val sample = step()
      if (sample.r.nonEmpty) return sample.r.get
    }
    throw new AssertionError(s"R response timeout on address $addr")
  }

  private def finishR(expected: (Long, Int)): Unit = {
    bus.r.ready #= true
    assert(step().r.contains(expected), "R changed before consumption")
    bus.r.ready #= false
  }

  private def read(addr: Int, expected: Int = Okay): Long = {
    val response = beginRead(addr)
    assert(response._2 == expected, s"address $addr: R response ${response._2} != $expected")
    for (_ <- 0 until (arCount % 5).toInt) assert(step().r.contains(response))
    finishR(response)
    response._1
  }

  def execute(instruction: Long): Unit = write(Instruction, instruction)
  def selectPhase(phase: Int): Unit = {
    write(Phase, phase)
    activePhase = phase
    phaseWrites += 1
  }
  def selector(edge: Int): Unit = {
    write(Selector, edge)
    selectorWrites += 1
  }
  def clearCorrection(): Unit = write(CorrectionClear, 0)
  def accumulate(edge: Int): Unit = {
    write(CorrectionEdge, edge)
    xorWrites += 1
  }

  def correctionRead(): (Int, String) = {
    write(LatchCorrection, 0)
    val generation = read(SnapshotGeneration)
    val meta = read(SnapshotMeta)
    assert((meta >>> 31) == 1 && ((meta >>> 16) & 3) == activePhase, "wrong snapshot phase")
    val count = (meta & 0xffff).toInt
    assert(count == dut.config.phaseBanks(activePhase).faultIdCount, "wrong snapshot length")
    val words = (count + 31) / 32
    val vector = (0 until words).foldLeft(BigInt(0)) { (acc, word) =>
      acc | (BigInt(read(CorrectionBase + 4 * word)) << (32 * word))
    }
    assert(vector.bitLength <= count && read(SnapshotGeneration) == generation, "torn correction")
    vectors += 1
    vectorWords += words
    (count, vector.toString(16))
  }

  private def obstacle(): (DataMaxGrowable, DataConflictRaw) = {
    execute(spec.generateFindObstacle())
    obstacleReads += 1
    val growable = DataMaxGrowable(read(Growable).toInt)
    if (read(ConflictValid) == 0) {
      val none = dut.ioConfig.IndexNone
      (growable, DataConflictRaw(false, none, none, none, none, none, none))
    } else {
      def unpack(word: Long): (Int, Int) = ((word & 0xffff).toInt, (word >>> 16).toInt)
      val (n1, n2) = unpack(read(ConflictNodes))
      val (t1, t2) = unpack(read(ConflictTouches))
      val (v1, v2) = unpack(read(ConflictVertices))
      (growable, DataConflictRaw(true, n1, n2, t1, t2, v1, v2))
    }
  }

  def findObstacle(maxGrowth: Long): (DataMaxGrowable, DataConflictRaw, Long) = {
    var (growable, conflict) = obstacle()
    var grown = 0L
    while (!conflict.valid && growable.length > 0 && growable.length != dut.ioConfig.LengthNone &&
      grown < maxGrowth) {
      val length = math.min(growable.length.toLong, maxGrowth - grown)
      execute(spec.generateGrow(length))
      grown += length
      val next = obstacle()
      growable = next._1
      conflict = next._2
    }
    (growable, conflict, grown)
  }

  private def probePendingWrite(): Unit = {
    drivePair(Phase, 0, 15, 0, 0)
    assert(awaitB() == Okay)
    // Hold the next command VALID while the earlier B cannot retire.
    bus.aw.addr #= Phase
    bus.aw.valid #= true
    bus.w.data #= 1
    bus.w.strb #= 15
    bus.w.valid #= true
    for (_ <- 0 until 5) {
      val sample = step()
      assert(!sample.awFire && !sample.wFire && sample.b.contains(Okay))
    }
    finishB(Okay)
    drivePair(Phase, 1, 15, 0, 0)
    assert(awaitB() == Okay)
    finishB(Okay)
    activePhase = 1
    write(LatchCorrection, 0)
    assert(((read(SnapshotMeta) >>> 16) & 3) == 1, "queued phase command lost or reordered")
  }

  def directedProbes(): Unit = {
    assert(read(SnapshotMeta) == 0)
    assert(read(CorrectionBase, SlaveError) == 0)
    assert(read(0xfc, SlaveError) == 0)
    probePendingWrite()
    write(Phase, 0)
    activePhase = 0
    write(CorrectionClear, 0)
    val faultMap = dut.config.phaseBanks.head.edgeFaultIds
    val edge = faultMap.indexWhere(ids => ids.exists(_ >= 32) && ids.distinct.size == ids.size)
    assert(edge >= 0, "probe needs a nonzero correction word above word zero")
    val faults = faultMap(edge)
    val selectedWord = faults.find(_ >= 32).get / 32
    val expected = faults.filter(_ / 32 == selectedWord).foldLeft(0L) { (word, id) =>
      word ^ (1L << (id % 32))
    }
    val address = CorrectionBase + selectedWord * 4
    write(CorrectionEdge, edge)
    write(LatchCorrection, 0)
    val generation = read(SnapshotGeneration)
    val held = beginRead(address)
    assert(held == ((expected, Okay)), "incorrect nonzero correction before backpressure")
    // Change the live phase and publish a new snapshot before consuming the older R beat.
    write(Phase, 2)
    activePhase = 2
    write(LatchCorrection, 0)
    finishR(held)
    assert(read(SnapshotGeneration) == generation + 1)
    val phaseTwo = read(SnapshotMeta)
    assert(((phaseTwo >>> 16) & 3) == 2 && (phaseTwo & 0xffff) == dut.config.phaseBanks(2).faultIdCount)
    assert(read(address) == 0, "phase change did not clear live correction")

    write(Phase, 3, expected = SlaveError)
    write(Phase, 1, strobe = 7, expected = SlaveError)
    write(CorrectionEdge, dut.config.edgeNum, expected = SlaveError)
    write(Selector, dut.config.edgeNum, expected = SlaveError)
    write(Phase + 1, 1, expected = SlaveError)
    write(Instruction, spec.generateLoadWeightsExternal(), expected = SlaveError)
    write(LatchCorrection, 0)
    assert(read(SnapshotMeta) == phaseTwo, "rejected commands changed phase metadata")
    val closingWords = (dut.config.phaseBanks(2).faultIdCount + 31) / 32
    assert((0 until closingWords).forall(word => read(CorrectionBase + 4 * word) == 0),
      "rejected commands changed the correction")
    println("AXI_PHASE_PROBES_PASS held_b_queued_write=1 held_r_snapshot_swap=1 invalid_writes=6 invalid_reads=2")
  }

  def report(): Unit = {
    assert(awCount == wCount && wCount == bCount && arCount == rCount, "lost AXI handshakes")
    assert(addressFirst > 0 && dataFirst > 0 && simultaneous > 0 && bStallCycles > 0 && rStallCycles > 0)
    assert(vectors > 0 && obstacleReads > 0 && errorB == 6 && errorR == 2)
    println(s"AXI_PHASE_TRANSPORT_PASS aw=$awCount w=$wCount b=$bCount ar=$arCount r=$rCount " +
      s"aw_first=$addressFirst w_first=$dataFirst simultaneous=$simultaneous b_stalls=$bStallCycles " +
      s"r_stalls=$rStallCycles b_errors=$errorB r_errors=$errorR phase_writes=$phaseWrites " +
      s"selector_writes=$selectorWrites xor_writes=$xorWrites snapshots=$vectors vector_words=$vectorWords " +
      s"obstacle_reads=$obstacleReads simulated_bus_cycles=$cycles")
  }
}
