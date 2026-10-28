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
  background.draw_text(0, 65, 640, 40, 'Hold Cancel 1s to exit; 30s limit', 1)
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
  controlled_bitmap = Bitmap.new(40, 40)
  controlled_bitmap.fill_rect(0, 0, 40, 40, Color.new(255, 0, 255))
  objects << controlled_bitmap
  controlled = Sprite.new
  controlled.bitmap = controlled_bitmap
  controlled.x, controlled.y, controlled.z = 300, 350, 20
  objects << controlled
  hud_bitmap = Bitmap.new(640, 90)
  objects << hud_bitmap
  hud = Sprite.new
  hud.bitmap = hud_bitmap
  hud.y, hud.z = 120, 30
  objects << hud
  feedback = 'D-pad moves pink square; Confirm replays tone'
  previous_feedback = nil
  cancel_frames = 0

  # Quiet, original 440 Hz PCM tone, generated only inside the isolated work dir.
  rate = 22050
  sample_count = rate * 3 / 5
  samples = Array.new(sample_count) do |i|
    envelope = [i / 220.0, (sample_count - 1 - i) / 220.0, 1.0].min
    (Math.sin(2.0 * Math::PI * 440 * i / rate) * 6000 * envelope).to_i
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
    controlled.x -= 4 if Input.press?(Input::LEFT)
    controlled.x += 4 if Input.press?(Input::RIGHT)
    controlled.y -= 4 if Input.press?(Input::UP)
    controlled.y += 4 if Input.press?(Input::DOWN)
    controlled.x = [[controlled.x, 0].max, 600].min
    controlled.y = [[controlled.y, 210].max, 440].min
    if frame == 60 || frame == 600 || Input.trigger?(Input::C)
      # mkxp-z volume 40 means -21 dB, not 40% amplitude. 85 is about -5.25 dB.
      Audio.se_play('tone.wav', 85, 100)
      trace("SMOKE_AUDIO_REQUEST frame=#{frame} volume=85 duration_ms=600")
      feedback = 'TONE REQUESTED (not proof of audible sound)'
    end
    %i[DOWN LEFT RIGHT UP A B C X Y Z L R].each do |name|
      if Input.trigger?(Input.const_get(name))
        trace("SMOKE_INPUT #{name} frame=#{frame}")
        feedback = "RGSS input: #{name} (physical label may differ)"
      end
    end
    cancel_frames = Input.press?(Input::B) ? cancel_frames + 1 : 0
    if feedback != previous_feedback
      hud_bitmap.clear
      hud_bitmap.fill_rect(0, 0, 640, 90, Color.new(0, 0, 0, 230))
      hud_bitmap.draw_text(0, 0, 640, 40, feedback, 1)
      hud_bitmap.draw_text(0, 42, 640, 40, 'White = automatic; pink = your D-pad', 1)
      previous_feedback = feedback
    end
    if cancel_frames >= 60
      trace('SMOKE_EXIT cancel_hold')
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
