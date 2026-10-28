# SPDX-License-Identifier: MIT
# Original procedural RGSS1 fixture. No game, RTP, fonts, images or recorded sound.
STDOUT.sync = true
def trace(message)
  STDOUT.write(message + "\n")
end

trace("SMOKE_RUBY_BEGIN ruby=#{RUBY_VERSION} platform=#{RUBY_PLATFORM}")
raise 'unexpected Ruby version' unless RUBY_VERSION == '3.1.3'
raise 'unexpected platform' unless RUBY_PLATFORM == 'aarch64-linux'

objects = []
normal = false
begin
  Graphics.frame_rate = 60
  background = Bitmap.new(640, 480)
  objects << background
  [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0]].each_with_index do |rgb, i|
    background.fill_rect(i * 160, 0, 160, 480, Color.new(*rgb))
  end
  # Text uses the engine's already embedded fallback, not an imported font.
  background.draw_text(0, 20, 640, 40, 'MKXP H700: RED GREEN BLUE YELLOW', 1)
  background.draw_text(0, 65, 640, 40, 'D-pad + buttons; Cancel exits; 30s limit', 1)
  sprite = Sprite.new
  sprite.bitmap = background
  objects << sprite
  marker_bitmap = Bitmap.new(32, 32)
  marker_bitmap.fill_rect(0, 0, 32, 32, Color.new(255, 255, 255))
  objects << marker_bitmap
  marker = Sprite.new
  marker.bitmap = marker_bitmap
  marker.z = 10
  marker.y = 250
  objects << marker

  # Quiet, original 440 Hz PCM tone, generated only inside the isolated work dir.
  rate = 22050
  samples = Array.new(rate / 5) do |i|
    envelope = [i / 220.0, (rate / 5 - i) / 220.0, 1.0].min
    (Math.sin(2.0 * Math::PI * 440 * i / rate) * 3000 * envelope).to_i
  end.pack('s<*')
  wave = 'RIFF' + [36 + samples.bytesize].pack('V') + 'WAVEfmt ' +
         [16, 1, 1, rate, rate * 2, 2, 16].pack('VvvVVvv') +
         'data' + [samples.bytesize].pack('V') + samples
  File.binwrite('tone.wav', wave)
  trace('SMOKE_SETUP_PASS')

  1800.times do |frame|
    marker.x = (frame * 3) % 608
    Graphics.update
    Input.update
    trace("SMOKE_FRAME #{frame}") if frame % 300 == 0
    if frame == 60 || frame == 600
      Audio.se_play('tone.wav', 40, 100)
      trace("SMOKE_AUDIO_REQUEST frame=#{frame}")
    end
    %i[DOWN LEFT RIGHT UP A B C X Y Z L R].each do |name|
      trace("SMOKE_INPUT #{name} frame=#{frame}") if Input.trigger?(Input.const_get(name))
    end
    if Input.trigger?(Input::B)
      trace('SMOKE_EXIT cancel')
      break
    end
    trace('SMOKE_EXIT frame_limit') if frame == 1799
  end
  normal = true
rescue Exception => error
  trace("SMOKE_FAIL #{error.class}: #{error.message}")
  raise
ensure
  Audio.se_stop rescue nil
  objects.reverse_each { |object| object.dispose rescue nil }
  trace(normal ? 'SMOKE_SCRIPT_PASS' : 'SMOKE_SCRIPT_INCOMPLETE')
end
