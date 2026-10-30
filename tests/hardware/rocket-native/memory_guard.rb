# SPDX-License-Identifier: MIT
# Diagnostic-only early stop. No saving, GC or driver calls. A large/blocking
# native allocation between updates can still exceed the cutoff.
module NextUIRocketGuard
  @started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  @frames = 0

  def self.check
    @frames += 1
    return unless @frames % 10 == 0
    rss = File.read('/proc/self/statm').split[1].to_i * 4096
    elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - @started
    return unless rss > 400 * 1024 * 1024 || elapsed > 90
    warn "ROCKET_DIAGNOSTIC_STOP rss_bytes=#{rss} elapsed=#{elapsed.round(2)}"
    exit(0)
  end
end

class << Graphics
  alias_method :nextui_rocket_guard_update, :update
  def update(*args)
    NextUIRocketGuard.check
    nextui_rocket_guard_update(*args)
  end
end
