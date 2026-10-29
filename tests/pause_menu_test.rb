# SPDX-License-Identifier: MIT
# Host tests for rgss/pause_menu.rb with minimal synthetic RGSS stand-ins.
require 'minitest/autorun'
require 'tmpdir'

class Color
  def initialize(*rgba) = @rgba = rgba
end

class Font
  attr_accessor :color
end

class Bitmap
  attr_reader :width, :height, :font, :texts
  @fail = false
  class << self
    attr_accessor :fail, :live
  end
  self.live = 0

  def initialize(width, height)
    raise 'synthetic bitmap failure' if Bitmap.fail
    @width, @height, @font, @texts = width, height, Font.new, []
    Bitmap.live += 1
  end

  def fill_rect(*) = nil
  def clear = @texts.clear
  def draw_text(_x, _y, _w, _h, text, _align) = @texts << text
  def dispose = Bitmap.live -= 1
end

class Viewport
  attr_accessor :z
  def initialize(*) = nil
  def dispose = nil
end

class Sprite
  attr_accessor :bitmap, :x, :y
  def initialize(_viewport) = nil
  def dispose = nil
end

module Graphics
  class << self
    attr_accessor :frame_count
    def update = @frame_count += 1
    def width = 640
    def height = 480
  end
  self.frame_count = 0
end

module Audio
  class << self
    attr_reader :fades
    def reset = @fades = []
    %i[bgm_fade bgs_fade me_fade].each { |name| define_method(name) { |ms| @fades << [name, ms] } }
  end
  reset
end

# Frame-scripted SDL input: each update consumes one set of held buttons.
module Input
  DOWN, UP, B, C = 2, 8, 12, 13
  class << self
    attr_accessor :script, :updates
    def update
      @updates += 1
      @previous = @held || []
      @held = @script.shift || []
    end
    def press?(key) = @held.include?(key)
    def trigger?(key) = @held.include?(key) && !@previous.include?(key)
    def repeat?(key) = trigger?(key)
    def reset(script = [])
      @script, @updates, @held, @previous = script, 0, [], []
    end
  end
  reset
end

class Interpreter
  attr_accessor :running
  def running? = @running
end

class Game_System
  attr_accessor :save_disabled, :sounds
  attr_reader :map_interpreter
  def initialize = (@map_interpreter, @sounds = Interpreter.new, [])
  def se_play(sound) = @sounds << sound
end

class Game_Temp
  attr_accessor :save_calling, :message_window_showing, :last_file_index
end

DataSystem = Struct.new(:cursor_se, :decision_se, :cancel_se, :buzzer_se)

class Scene_Map
  def call_save = nil
end

class Scene_Title; end
class Scene_Save; end

class Scene_File
  attr_reader :started_with
  def main = @started_with = $game_temp
end

class Scene_Load < Scene_File
  def initialize = $game_temp = Game_Temp.new
  def on_cancel = $scene = Scene_Title.new
end

load File.expand_path('../rgss/pause_menu.rb', __dir__)

class PauseMenuTest < Minitest::Test
  MENU, SELECT = NextUIPause::KEY_CODE, 310

  def setup
    @reader, @writer = IO.pipe
    NextUIPause.use_input(@reader)
    NextUIPause.instance_variable_set(:@disabled, false)
    Bitmap.fail = false
    Bitmap.live = 0
    Audio.reset
    Graphics.frame_count = 100
    $scene = Scene_Map.new
    $game_temp = Game_Temp.new
    $game_system = Game_System.new
    $data_system = DataSystem.new(:cursor, :decision, :cancel, :buzzer)
  end

  def teardown
    [@reader, @writer].each { |io| io.close unless io.closed? }
  end

  def key(code, value, type = 1)
    @writer.write([0, 0, type, code, value].pack(NextUIPause::EVENT))
  end

  def press_menu
    key(MENU, 1)
    key(MENU, 0)
    key(0, 0, 0)
  end

  # Open the menu on the next game frame, then feed the scripted SDL frames.
  def run_menu(*frames)
    press_menu
    Input.reset([[]] + frames) # the first frame belongs to the game's own update
    Input.update
  end

  def test_finds_named_evdev_node
    Dir.mktmpdir do |dir|
      listing = File.join(dir, 'devices')
      File.write(listing, "I: Bus=0019\nN: Name=\"axp2202-pek\"\nH: Handlers=kbd event0 \n\n" \
                          "I: Bus=0019\nN: Name=\"ANBERNIC-keys\"\nH: Handlers=kbd js0 event1 \n\n")
      assert_equal '/dev/input/event1', NextUIPause.find_device(listing)
      File.write(listing, "N: Name=\"other\"\nH: Handlers=kbd event3\n")
      assert_nil NextUIPause.find_device(listing)
      assert_nil NextUIPause.find_device(File.join(dir, 'missing'))
    end
  end

  def test_unused_menu_passes_through
    key(SELECT, 1)
    key(314, 1) # L2 must not open the menu
    key(MENU, 2) # autorepeat is not a fresh press
    key(MENU, 1, 4)
    Input.reset([[Input::C]])
    Input.update
    assert_equal 1, Input.updates
    assert Input.trigger?(Input::C)
    assert_equal 100, Graphics.frame_count
    assert_equal 0, Bitmap.live
  end

  def test_continue_with_cancel_or_menu_restores_play_time
    run_menu([], [], [Input::B])
    assert_instance_of Scene_Map, $scene
    assert_equal 100, Graphics.frame_count
    assert_equal 0, Bitmap.live
  end

  def test_menu_button_closes_menu
    press_menu
    Input.reset
    writer = Thread.new { sleep 0.05; press_menu } # pressed again while the menu is open
    Input.update
    writer.join
    assert_instance_of Scene_Map, $scene
    refute $game_temp.save_calling
    assert_equal 0, Bitmap.live
  end

  def test_save_uses_the_games_save_call
    run_menu([Input::DOWN], [], [Input::C])
    assert $game_temp.save_calling
    assert_instance_of Scene_Map, $scene
    assert_includes $game_system.sounds, :decision
  end

  def test_save_unavailable_during_events_or_when_disabled
    $game_system.map_interpreter.running = true
    run_menu([Input::DOWN], [], [Input::C], [], [Input::B])
    refute $game_temp.save_calling
    assert_includes $game_system.sounds, :buzzer
    $game_system.map_interpreter.running = false
    $game_system.save_disabled = true
    run_menu([Input::DOWN], [], [Input::C], [], [Input::B])
    refute $game_temp.save_calling
  end

  def test_load_opens_load_screen_and_cancel_returns_to_map
    Dir.mktmpdir do |dir|
      Dir.chdir(dir) do
        File.write('Save2.rxdata', 'synthetic')
        map_temp = $game_temp
        run_menu([Input::DOWN], [], [Input::DOWN], [], [Input::C])
        assert_instance_of Scene_Load, $scene
        assert_same map_temp, $game_temp # untouched until the load screen starts
        load_scene = $scene
        load_scene.main
        refute_same map_temp, load_scene.started_with
        load_scene.on_cancel
        assert_instance_of Scene_Map, $scene
        assert_same map_temp, $game_temp
      end
    end
  end

  def test_load_unavailable_without_saves
    Dir.mktmpdir do |dir|
      Dir.chdir(dir) do
        run_menu([Input::DOWN], [], [Input::DOWN], [], [Input::C], [], [Input::B])
        assert_instance_of Scene_Map, $scene
        assert_includes $game_system.sounds, :buzzer
      end
    end
  end

  def test_quit_requires_confirmation
    quit = [[Input::UP], [], [Input::C], []]
    run_menu(*quit, [Input::C]) # "Cancel" is preselected
    assert_instance_of Scene_Map, $scene
    assert_empty Audio.fades
    run_menu(*quit, [Input::DOWN], [], [Input::C])
    assert_nil $scene
    assert_equal [[:bgm_fade, 800], [:bgs_fade, 800], [:me_fade, 800]], Audio.fades
  end

  def test_held_confirm_does_not_reach_the_game
    run_menu([Input::B], [Input::B], [Input::B], [])
    refute Input.press?(Input::B)
    refute Input.trigger?(Input::B)
    assert_operator Input.updates, :>=, 5
  end

  def test_overlay_failure_never_breaks_the_game
    Bitmap.fail = true
    _, err = capture_io do
      run_menu([Input::B])
    end
    assert_match(/NEXTUI_PAUSE_ERROR=RuntimeError/, err)
    assert_instance_of Scene_Map, $scene
    Bitmap.fail = false
    run_menu([Input::B]) # stays disabled; update still works
    assert_instance_of Scene_Map, $scene
  end

  def test_input_disconnect_disables_menu_quietly
    @writer.close
    Input.reset([[]])
    Input.update
    assert_nil NextUIPause.instance_variable_get(:@io)
    Input.update
    assert_equal 2, Input.updates
  end

  def test_outside_map_only_continue_and_quit
    $scene = Scene_Title.new
    run_menu([Input::DOWN], [], [Input::C], [], [Input::B])
    refute $game_temp.save_calling
    assert_instance_of Scene_Title, $scene
  end
end
