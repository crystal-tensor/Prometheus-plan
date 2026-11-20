package microblossom

/** Direct-load check for the six frozen d=6 graph images.
  *
  * Compile this object inside the pinned Micro Blossom source tree and pass
  * the six image paths as positional arguments.  It intentionally checks
  * parsing/configuration only; it does not award RTL or timing credit.
  */
object D6MicroBlossomImageLoadCheck extends App {
  require(args.length == 6, s"expected six graph images, got ${args.length}")
  args.foreach { path =>
    val config = new DualConfig(filename = path, hardCodeWeights = false)
    config.sanityCheck()
    val maximumWeight = config.graph.weighted_edges.map(_.w).max
    require(config.edgeNum < (1 << 15), s"$path: edge index exceeds 15 bits")
    require(maximumWeight <= 65535, s"$path: stored weight exceeds 16 bits")
    require(config.weightBits <= 16, s"$path: inferred weightBits exceeds 16")
    println(
      s"DIRECT_LOAD_PASS path=$path vertices=${config.vertexNum} " +
        s"edges=${config.edgeNum} weightBits=${config.weightBits} " +
        s"maximumWeight=$maximumWeight"
    )
  }
}
