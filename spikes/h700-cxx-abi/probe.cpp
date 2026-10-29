// SPDX-License-Identifier: MIT
// Original game-free C++14 lifetime/exception/allocation calibration.
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string>

static int alive = 0;
static int destroyed = 0;

struct Lifetime {
    Lifetime() { ++alive; }
    ~Lifetime() { --alive; ++destroyed; }
    Lifetime(const Lifetime&) = delete;
    Lifetime& operator=(const Lifetime&) = delete;
};

static void unwind(const std::string& text) {
    Lifetime guard;
    auto payload = std::make_unique<std::string[]>(2);
    payload[0] = text;
    payload[1] = std::string(256, 'x'); // Force more than small-string storage.
    if (payload[0] == "h700-cxx14" && payload[1].size() == 256)
        throw std::runtime_error(payload[0]);
    throw std::logic_error("unexpected payload");
}

int main() {
    bool caught = false;
    {
        Lifetime outer;
        auto label = std::make_unique<std::string>("h700-");
        label->append("cxx14");
        try {
            unwind(*label);
        } catch (const std::runtime_error& error) {
            caught = std::string(error.what()) == *label;
        } catch (...) {
            return 11;
        }
        if (!caught || alive != 1 || destroyed != 1) return 12;
    }
    if (alive != 0 || destroyed != 2) return 13;
    std::puts("RMXP_CXX14 native_or_target_probe_ok destructors=2");
    return 0;
}
