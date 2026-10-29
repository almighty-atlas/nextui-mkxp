# SPDX-License-Identifier: MIT
# Host tests for rgss/essentials_win32_compat.rb with synthetic RGSS stand-ins.
# The "game" side below is original test code shaped like Essentials' usage.
require 'minitest/autorun'
require 'tmpdir'

module Graphics
  class << self
    attr_accessor :frame_count
    def update = @frame_count += 1
    def width = 640
    def height = 480
  end
  self.frame_count = 0
end

# mkxp-z RGSS1 native Input: integer button codes, module functions.
module Input
  DOWN, LEFT, RIGHT, UP = 2, 4, 6, 8
  A, B, C, X, Y, Z, L, R = 11, 12, 13, 14, 15, 16, 17, 18
  SHIFT, CTRL, ALT = 21, 22, 23
  F5, F6, F7, F8, F9 = 25, 26, 27, 28, 29

  class << self
    attr_accessor :held, :native_updates
    def update = @native_updates += 1
    def press?(button) = @held.include?(button)
  end
  self.held = []
  self.native_updates = 0
end

Dir.chdir(Dir.mktmpdir('nextui-win32')) do
  load File.expand_path('../rgss/essentials_win32_compat.rb', __dir__)
  $written = Dir.children('.')
end

# Synthetic game side: reopen Win32API, build handles in the class body and
# replace the native Input module functions like Essentials' controls do.
class Win32API
  @@thread = Win32API.new('kernel32', 'GetCurrentThreadId', '%w()', 'l')
  @@owner = Win32API.new('user32', 'GetWindowThreadProcessId', '%w(l p)', 'l')
  @@find = Win32API.new('user32', 'FindWindowEx', '%w(l l p p)', 'l')

  def self.find_window
    window = 0
    loop do
      window = @@find.call(0, window, 'RGSS Player', 0)
      return window if window != 0 && @@owner.call(window, [0].pack('l')) == @@thread.call
      raise "Can't find RGSS player window" if window == 0
    end
  end
end

module Input
  @key_state = Win32API.new('user32', 'GetAsyncKeyState', 'i', 'i')
  def self.update = @game_updates = (@game_updates || 0) + 1
  def self.press?(_button) = raise('game replacement must not be used by the shim')
  def self.down?(key) = (@key_state.call(key) & 0x8000) > 0
end

module FontInstaller
  def self.install = raise('must be replaced')
  def self.kept = :kept
end

class EssentialsWin32CompatTest < Minitest::Test
  def setup
    Input.held = []
    Input.native_updates = 0
    Graphics.frame_count += 1
  end

  def call(dll, function, *args)
    Win32API.new(dll, function, 'x', 'x').call(*args)
  end

  def test_constructor_accepts_essentials_signatures_and_class_reopening
    assert_equal 1, Win32API.find_window
    assert_equal 0, Win32API.new('Kernel32.dll', 'LoadLibrary', 'p', '').call('gif.dll')
    assert_equal 0, Win32API.new('gdi32', 'AddFontResource', ['P'], 'L').Call('font.ttf')
  end

  def test_virtual_keys_report_native_buttons_from_gamepad_bindings
    refute Input.down?(0x0D)
    Graphics.frame_count += 1
    Input.held = [Input::C]
    assert Input.down?(0x0D)
    refute Input.down?(0x1B)
    refute Input.down?(0x7B) # unmapped F12
  end

  def test_registered_item_key_and_directions
    Input.held = [Input::X, Input::LEFT]
    assert Input.down?(0x74)
    assert Input.down?(0x25)
    refute Input.down?(0x27)
  end

  def test_each_button_reports_a_single_virtual_key
    # Several pressed aliases would re-trigger on later frames in Essentials.
    targets = NextUIWin32::KEYS.values.flatten
    assert_equal targets.uniq.size, targets.size
    Input.held = [Input::C, Input::B, Input::A]
    assert_equal [0x0D, 0x1B, 0x5A], (0..255).select { |key| Input.down?(key) }
  end

  def test_native_update_runs_once_per_frame_even_after_game_replaced_it
    5.times { Input.down?(0x28) }
    assert_equal 1, Input.native_updates
    Graphics.update
    Input.down?(0x28)
    assert_equal 2, Input.native_updates
  end

  def test_window_rect_buffers_and_metrics
    rect = [0, 0, 0, 0].pack('l4')
    assert_equal 1, call('user32', 'GetClientRect', 1, rect)
    assert_equal [0, 0, 640, 480], rect.unpack('l4')
    short = "\0" * 4
    assert_equal 0, call('user32', 'GetWindowRect', 1, short)
    assert_equal "\0" * 4, short
    assert_equal [640, 480, 0], [0, 1, 80].map { |i| call('user32', 'GetSystemMetrics', i) }
  end

  def test_unavailable_apis_fail_safely
    key = "\0" * 4
    assert_equal 2, call('advapi32', 'RegOpenKeyExA', 0x80000001, 'Software', 0, 0x20019, key)
    assert_equal "\0" * 4, key
    assert_operator call('shell32', 'SHGetKnownFolderPath', '', 0, 0, "\0" * 4), :<, 0
    assert_operator call('shell32', 'SHGetSpecialFolderLocation', 0, 5, "\0" * 4), :<, 0
    refute_equal 0, call('winmm', 'mciSendString', 'status cdaudio media present', "\0" * 8, 8, 0)
    assert_equal 0, call('RMFlash', '_is_playing', 0)
    assert_equal 0, call('kernel32', 'GetSystemPowerStatus', "\0" * 12)
    assert_equal 0x0409, call('kernel32', 'GetUserDefaultLangID') & 0xFFFF
  end

  def test_font_installer_neutralized_without_touching_other_methods
    assert_nil FontInstaller.install
    assert_equal :kept, FontInstaller.kept
  end

  def test_loading_writes_no_files
    assert_empty $written
  end
end
