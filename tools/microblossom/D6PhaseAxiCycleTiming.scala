package microblossom

import java.nio.charset.StandardCharsets
import java.security.MessageDigest

/** Measured rising-edge counts of the serialized simulation bus manager. */
final case class D6AxiCycleTally(
    cycles: Long = 0, writes: Long = 0, reads: Long = 0,
    bStalls: Long = 0, rStalls: Long = 0, awWSkew: Long = 0
) {
  def +(b: D6AxiCycleTally): D6AxiCycleTally = D6AxiCycleTally(
    cycles + b.cycles, writes + b.writes, reads + b.reads,
    bStalls + b.bStalls, rStalls + b.rStalls, awWSkew + b.awWSkew
  )
  def -(b: D6AxiCycleTally): D6AxiCycleTally = D6AxiCycleTally(
    cycles - b.cycles, writes - b.writes, reads - b.reads,
    bStalls - b.bStalls, rStalls - b.rStalls, awWSkew - b.awWSkew
  )
  def csv: String = s"$cycles,$writes,$reads,$bStalls,$rStalls,$awWSkew"
}

final class D6PhaseAxiCycleTiming(val policy: String, readLatency: Int) {
  val labels = Vector("ingress", "solve_cmd", "obstacle_read", "correction_write", "correction_read")
  require(Set("ready_high", "legacy_hold").contains(policy), s"unknown AXI timing policy $policy")
  require(readLatency > 0)
  private final case class Window(
      shot: Int, index: Int, phase: Int, start: D6AxiCycleTally,
      groups: Array[D6AxiCycleTally], sequence: MessageDigest
  )
  private var window: Option[Window] = None
  private var count = 0
  private var summed = D6AxiCycleTally()

  def active: Boolean = window.nonEmpty
  def acceptImmediately: Boolean = active && policy == "ready_high"

  def begin(shot: Int, index: Int, phase: Int, start: D6AxiCycleTally): Unit = {
    require(!active, "previous cycle window not closed")
    require(shot >= 0 && index >= 0 && phase >= 0 && phase < 3, "invalid cycle window key")
    window = Some(Window(shot, index, phase, start, Array.fill(labels.length)(D6AxiCycleTally()),
      MessageDigest.getInstance("SHA-256")))
  }

  def record(stage: Int, verb: String, address: Int, data: Long, mask: Int, response: Int,
             delta: D6AxiCycleTally): Unit = {
    val current = window.getOrElse(throw new IllegalStateException("operation outside cycle window"))
    val expected = if (verb == "W") (1L, 0L) else (0L, 1L)
    require((delta.writes, delta.reads) == expected && response == D6PhaseAxiMap.Okay,
      "wrong accepted transaction count inside a measured operation")
    if (acceptImmediately) require(delta.bStalls == 0 && delta.rStalls == 0, "READY was withheld")
    current.groups(stage) = current.groups(stage) + delta
    val text = s"$stage $verb $address $data $mask $response\n"
    current.sequence.update(text.getBytes(StandardCharsets.US_ASCII))
  }

  def finish(activePhase: Int, end: D6AxiCycleTally): Unit = {
    val current = window.getOrElse(throw new IllegalStateException("missing cycle window marker"))
    require(activePhase == current.phase, "cycle window ended in wrong phase")
    val delta = end - current.start
    require(current.groups.foldLeft(D6AxiCycleTally())(_ + _) == delta, "unattributed measured cycles")
    val digest = current.sequence.digest().map(b => f"${b & 0xff}%02x").mkString
    val groups = labels.zip(current.groups).map { case (key, total) => s"$key=${total.csv}" }.mkString(" ")
    println(s"AXI_CYCLE_WINDOW mode=$policy shot=${current.shot} window=${current.index} phase=${current.phase} " +
      s"b_start=${current.start.writes} r_start=${current.start.reads} tx_sha256=$digest total=${delta.csv} $groups")
    summed = summed + delta
    count += 1
    window = None
  }

  def report(): Unit = {
    require(!active && count > 0, "incomplete cycle profile")
    println(s"AXI_CYCLE_PROFILE mode=$policy read_latency=$readLatency windows=$count total=${summed.csv}")
  }
}
