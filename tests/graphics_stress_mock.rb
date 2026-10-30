# SPDX-License-Identifier: MIT
# Synthetic renderer for stress-script control flow, not rendering verification.
module Graphics
  class << self
    attr_accessor :frame_rate, :frames
    def resize_screen(*) = nil
    def update = self.frames += 1
  end
  self.frames = 0
end
class Bitmap
  @created = []
  class << self
    attr_reader :created
  end
  attr_reader :disposed
  def initialize(*)
    self.class.created << self
  end
  def dispose = @disposed = true
  def fill_rect(*) = nil
  def clear = nil
  def blt(*) = nil
end
class Sprite
  attr_accessor :bitmap
  def dispose = nil
end
class Rect
  attr_accessor :x, :y
  def initialize(*) = nil
end
class Color
  def initialize(*) = nil
end
class << File
  alias native_read read
  def read(path, *args)
    return ENV['STRESS_HIGH_RSS'] == '1' ? '200000 150000' : '20000 10000' if path == '/proc/self/statm'
    native_read(path, *args)
  end
end
begin
  load File.expand_path('hardware/graphics-stress/stress.rb', __dir__)
rescue SystemExit
  raise 'Unexpected early exit' unless ENV['STRESS_HIGH_RSS'] == '1'
end
raise 'Native wrappers not disposed' unless Bitmap.created.all?(&:disposed)
expected = ENV['STRESS_HIGH_RSS'] == '1' ? 0 : 2400
raise "Wrong frame count #{Graphics.frames}" unless Graphics.frames == expected
puts 'STRESS_CONTROL_FLOW_PASS'
