# SPDX-License-Identifier: MIT
# Original generated graphics only. No game/RTP files or save paths touched.
# Do not interpret completion as Rocket compatibility or driver correctness.
Graphics.resize_screen(512, 384)
Graphics.frame_rate = 40
started = Time.now
source = target = sprite = nil
begin
  target = Bitmap.new(832, 704)
  sprite = Sprite.new
  sprite.bitmap = target
  tile = Rect.new(0, 0, 32, 32)
  [512, 16064, 512].each_with_index do |height, phase|
    source.dispose if source
    source = Bitmap.new(256, height)
    source.fill_rect(0, 0, 256, height, Color.new(50, 130, 70))
    puts "GRAPHICS_STRESS_PHASE=#{phase} source=256x#{height}"
    800.times do |frame|
      if frame % 10 == 0
        pages = File.read('/proc/self/statm').split[1].to_i
        # H700 page size is 4096. Early diagnostic stop, not an OOM guarantee:
        # a single native operation may allocate memory between these checks.
        if pages * 4096 > 400 * 1024 * 1024 || Time.now - started > 70
          puts "GRAPHICS_STRESS_STOP rss_pages=#{pages} elapsed=#{Time.now - started}"
          exit
        end
      end
      target.clear
      22.times do |y|
        26.times do |x|
          tile.x = (x % 8) * 32
          tile.y = ((y + frame) % (height / 32)) * 32
          target.blt(x * 32, y * 32, source, tile)
        end
      end
      if phase == 2 && frame % 10 == 0
        copy = source.clone
        copy.dispose
      end
      Graphics.update
    end
  end
  puts 'GRAPHICS_STRESS_COMPLETE'
ensure
  sprite.dispose if sprite
  target.dispose if target
  source.dispose if source
end
