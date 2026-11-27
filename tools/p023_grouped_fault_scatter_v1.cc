// Apply syndrome and logical parities for packed Bernoulli bits.
// Only the application of fault flags is native; this file chooses no noise.

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>

extern "C" void p023_scatter_group_v1(
    const std::uint8_t *flags, std::size_t bit_count, std::size_t shots,
    const std::uint32_t *group, const std::uint32_t *offsets,
    const std::uint32_t *targets, std::uint8_t *detectors, std::size_t detector_width,
    std::uint8_t *observable) {
    // The host wrapper ensures a little-endian machine and nonzero shots.
    const bool power_of_two = (shots & (shots - 1)) == 0;
    const unsigned shot_bits = power_of_two ? __builtin_ctzll(shots) : 0;
    const std::size_t flag_bytes = (bit_count + 7) / 8;
    for (std::size_t pos = 0; pos < flag_bytes; pos += 8) {
        std::uint64_t word = 0;
        std::memcpy(&word, flags + pos, std::min<std::size_t>(8, flag_bytes - pos));
        while (word) {
            const auto bit = pos * 8 + __builtin_ctzll(word);
            word &= word - 1;
            if (bit >= bit_count) {
                break;  // The packed buffer can have final-byte padding.
            }
            const auto entry = power_of_two ? (bit >> shot_bits) : (bit / shots);
            const auto shot = power_of_two ? (bit & (shots - 1)) : (bit % shots);
            const std::uint32_t fault = group[entry];
            auto *row = detectors + shot * detector_width;
            for (std::uint32_t k = offsets[fault]; k < offsets[fault + 1]; ++k) {
                const auto t = targets[k];
                if (t == UINT32_MAX) {
                    observable[shot] ^= 1;
                } else {
                    row[t >> 3] ^= std::uint8_t{1} << (t & 7);
                }
            }
        }
    }
}
