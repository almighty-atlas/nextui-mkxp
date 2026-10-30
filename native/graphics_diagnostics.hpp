// SPDX-License-Identifier: MIT
// Diagnostic-only counters for the pinned mkxp-z GL wrapper, not GPU residency.
// Called on the engine's GL thread. No driver calls, game data or finalizers.
#ifndef NEXTUI_GRAPHICS_DIAGNOSTICS_HPP
#define NEXTUI_GRAPHICS_DIAGNOSTICS_HPP
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <unordered_map>

namespace NextUIGraphics {
struct Ledger {
    std::unordered_map<unsigned, uint64_t> textures;
    unsigned bound = 0;
    uint64_t generated = 0, deleted = 0, images = 0, subimages = 0;
    uint64_t imageBytes = 0, uploadBytes = 0, liveBytes = 0, peakBytes = 0;
    uint64_t blits = 0, poolBytes = 0, poolObjects = 0, reports = 0;
    uint64_t largeReports = 0;
    bool overflow = false;

    static uint64_t pixels(int w, int h) {
        return w > 0 && h > 0 ? uint64_t(w) * uint64_t(h) * 4 : 0;
    }
    void gen(unsigned id) {
        ++generated;
        if (textures.size() >= 65536) { overflow = true; return; }
        textures.emplace(id, 0);
    }
    void erase(unsigned id) {
        ++deleted;
        auto it = textures.find(id);
        if (it != textures.end()) { liveBytes -= it->second; textures.erase(it); }
        if (bound == id) bound = 0;
    }
    void image(int w, int h, bool upload) {
        ++images;
        auto bytes = pixels(w, h);
        imageBytes += bytes;
        if (upload) uploadBytes += bytes;
        auto it = textures.find(bound);
        if (it == textures.end()) { overflow = true; return; }
        liveBytes = liveBytes - it->second + bytes;
        it->second = bytes;
        if (liveBytes > peakBytes) peakBytes = liveBytes;
    }
    void subimage(int w, int h) { ++subimages; uploadBytes += pixels(w, h); }
};

inline bool enabled() {
    static const bool value = [] {
        const char *flag = std::getenv("NEXTUI_GL_DIAGNOSTICS");
        return flag && std::strcmp(flag, "1") == 0;
    }();
    return value;
}
inline Ledger &ledger() { static Ledger value; return value; }
inline void report(bool force = false) {
    if (!enabled()) return;
    auto &s = ledger();
    static auto last = std::chrono::steady_clock::now();
    auto now = std::chrono::steady_clock::now();
    if (s.reports >= 90 || (!force && now - last < std::chrono::seconds(2))) return;
    last = now;
    long pages = 0, rss = 0;
    FILE *f = std::fopen("/proc/self/statm", "r");
    if (f) { if (std::fscanf(f, "%ld %ld", &pages, &rss) != 2) rss = 0; std::fclose(f); }
    std::fprintf(stderr,
        "NEXTUI_GL gen=%llu del=%llu live=%zu bytes=%llu peak=%llu images=%llu "
        "image_bytes=%llu subimages=%llu upload_bytes=%llu blits=%llu "
        "pool_bytes=%llu pool_objects=%llu rss_pages=%ld incomplete=%d\n",
        (unsigned long long)s.generated, (unsigned long long)s.deleted, s.textures.size(),
        (unsigned long long)s.liveBytes, (unsigned long long)s.peakBytes,
        (unsigned long long)s.images, (unsigned long long)s.imageBytes,
        (unsigned long long)s.subimages, (unsigned long long)s.uploadBytes,
        (unsigned long long)s.blits, (unsigned long long)s.poolBytes,
        (unsigned long long)s.poolObjects, rss, s.overflow);
    std::fflush(stderr);
    ++s.reports;
}
inline void gen(unsigned id) { if (enabled()) ledger().gen(id); }
inline void erase(unsigned id) { if (enabled()) ledger().erase(id); }
inline void bind(unsigned id) { if (enabled()) ledger().bound = id; }
// Preserve a call site for offline addr2line. Only a small number of large
// image definitions are sampled; no stack walking or per-tile symbol lookup.
__attribute__((noinline)) inline void image(int w, int h, bool upload) {
    if (!enabled()) return;
    auto &s = ledger();
    s.image(w, h, upload);
    if (Ledger::pixels(w, h) >= 1024 * 1024 && s.largeReports < 32) {
        Dl_info info = {};
        void *pc = __builtin_return_address(0);
        bool resolved = dladdr(pc, &info) != 0 && info.dli_fbase;
        auto relative = resolved ? reinterpret_cast<uintptr_t>(pc) -
                                   reinterpret_cast<uintptr_t>(info.dli_fbase) : 0;
        std::fprintf(stderr,
            "NEXTUI_GL_IMAGE id=%u w=%d h=%d upload=%d bytes=%llu caller_offset=0x%llx resolved=%d\n",
            s.bound, w, h, upload, (unsigned long long)Ledger::pixels(w, h),
            (unsigned long long)relative, resolved);
        ++s.largeReports;
    }
    report();
}
inline void subimage(int w, int h) {
    if (enabled()) { ledger().subimage(w, h); report(); }
}
inline void blit() { if (enabled()) { ++ledger().blits; report(); } }
inline void pool(uint64_t bytes, uint64_t objects) {
    if (enabled()) { ledger().poolBytes = bytes; ledger().poolObjects = objects; }
}
}
#endif
