# SPDX-License-Identifier: MIT
# Host tests for rgss/essentials_win32_compat.rb with synthetic RGSS stand-ins.
# The "game" side below is original test code shaped like Essentials' usage.
require 'minitest/autorun'
require 'tmpdir'

# mkxp-z native Bitmap stand-in (size and dispose only).
class Bitmap
  attr_reader :width, :height
  attr_writer :frame_count
  def frame_count = @frame_count || 1
  def initialize(width, height) = (@width, @height, @disposed = width, height, false)
  def dispose = @disposed = true
  def disposed? = @disposed
end

module Graphics
  class << self
    attr_accessor :frame_count
    attr_reader :resized
    attr_accessor :nominal
    def update = @frame_count += 1
    def width = @nominal[0]
    def height = @nominal[1]
    def resize_screen(width, height) = @resized << [width, height]
  end
  self.frame_count = 0
  self.nominal = [640, 480]
  @resized = []
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

# Synthetic Ruby 1.8-style sections, decoded like mkxp-z's $RGSS_SCRIPTS.
$RGSS_SCRIPTS = [
  [1, 'Tones', '', "def tone(t)\r\n  case t\r\n  when 0: # low\r\n    :low\r\n  when 1, 2:\r\n    :high\r\n  when :x then :sym\r\n  end\r\nend\r\n"],
  [2, 'Json', '', "def plain?(s) = s[/\"[^\"\\\\\\x00-\\x1f\\x7f-\\x9f]*\"/]\n"],
  [3, 'Weather', '', "def clear(w)\n  if w == 1\n    @d=0.\n  elsif w == 2\n    @d=5.\n  end\n  @d\nend\n"],
  [4, 'Valid', '', "x = 1\n"],
  [5, 'Broken', '', "when 0:\n  def\n"],
  [6, 'Bytes', '', "# \xFF\nwhen_ok = 1\n".b.force_encoding('UTF-8')],
  [7, 'Folder', '', 0]
]
$ORIGINAL_SOURCES = $RGSS_SCRIPTS.map { |script| script[3].dup }

ENV.delete('TEMP')
ENV.delete('TMP')
$HOME = ENV['HOME'] = Dir.mktmpdir('nextui-home')
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

# Shaped like Essentials' StringInput: character indexing, as written for 1.8.
class StringInput
  def initialize(str)
    @string, @pos, @closed = str, 0, false
  end

  def getc
    ch = @string[@pos]
    @pos += 1
    ch
  end

  def gets
    idx = @string.index("\n", @pos)
    line = idx ? @string[@pos..idx] : @string[@pos..]
    @pos = idx ? idx + 1 : @string.size + 1
    line
  end

  def read(len)
    str = @string[@pos, len]
    @pos += len
    str
  end

  def each_byte
    while (byte = getc)
      yield byte
    end
  end
end

# Top-level handler procs with `return`, like Essentials' Events.onAction.
# mkxp-z evaluates each section with a nil binding from C, so the section's
# frame is gone when the handler runs; a method frame reproduces that here.
HANDLERS = []
def evaluate_section(code) = eval(code, nil, '116:PField_FieldMoves') # rubocop:disable Security/Eval
evaluate_section(<<~'RUBY')
  HANDLERS << proc { |value| return :skipped if value.nil?; :handled }
  HANDLERS << proc { |value| [1, 2].each { |item| break :from_block if item == value }; :done }
RUBY

# Games chain Graphics.update and Kernel#exit with alias (Essentials, RMFlash).
class << Graphics
  alias game_update update
  def update = game_update
end

module Kernel
  alias game_exit exit
  def exit(*args) = game_exit(*args)
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

  def test_ruby18_sections_repaired_in_memory_with_same_line_numbers
    sources = $RGSS_SCRIPTS.map { |script| script[3] }
    sources[0..2].each_with_index do |source, index|
      refute_equal $ORIGINAL_SOURCES[index], source
      assert_equal $ORIGINAL_SOURCES[index].lines.size, source.lines.size
      eval(source, TOPLEVEL_BINDING) # rubocop:disable Security/Eval
    end
    assert_equal %i[low high high sym], [0, 1, 2, :x].map { |t| tone(t) }
    assert_includes sources[0], 'when 0 then # low'
    assert_equal '"ok"', plain?('"ok"')
    assert_equal [0, 5], [1, 2].map { |w| clear(w) }
  end

  def test_valid_unrepairable_and_non_utf8_sections_left_untouched
    assert_equal $ORIGINAL_SOURCES[3..6], $RGSS_SCRIPTS[3..6].map { |script| script[3] }
  end

  def test_ruby18_core_methods_restored
    assert_equal 2, [1, nil, false, nil].nitems
    assert_equal :b, { a: 1, b: 2 }.index(2)
    assert_equal String, 'x'.type
    object = Object.new
    assert_equal object.object_id, object.id
    assert_equal [true, false, nil], [TRUE, FALSE, NIL]
    old = Thread.critical
    Thread.critical = true
    assert Thread.critical
    Thread.critical = old
    refute Thread.critical
  end

  def test_string_input_reads_bytes_like_ruby18
    data = [0x12345678].pack('V') + "\u00e9t\u00e9\nok\n"
    input = StringInput.new(data.dup.force_encoding('UTF-8'))
    value = 0
    4.times { |shift| value |= input.getc << (8 * shift) }
    assert_equal 0x12345678, value
    line = input.gets
    assert_equal "\u00e9t\u00e9\n", line
    assert_equal Encoding::UTF_8, line.encoding
    assert_equal 'ok', input.read(2)
    assert_equal ["a\n", 'b'], StringInput.new("a\nb").each.to_a
    assert_equal data.force_encoding('UTF-8'), input.string
  end

  def test_screen_follows_game_size_once_per_change
    Graphics.resized.clear
    Graphics.update
    assert_empty Graphics.resized
    Graphics.nominal = [512, 384]
    3.times { Graphics.update }
    assert_equal [[512, 384]], Graphics.resized
    $ResizeOffsetX, $ResizeOffsetY = 64, 48
    Graphics.update
    assert_equal [640, 480], Graphics.resized.last
  ensure
    $ResizeOffsetX = $ResizeOffsetY = nil
    Graphics.nominal = [640, 480]
    Graphics.update
  end

  def test_string_input_supports_marshal_load
    data = Marshal.dump([1, 'Pok\u00e9mon', { trainer: 7 }])
    assert_equal [1, 'Pok\u00e9mon', { trainer: 7 }], Marshal.load(StringInput.new(data))
  end

  def test_exit_and_scene_end_are_traced_in_log
    _out, err = capture_io do
      assert_raises(SystemExit) { exit(3) }
      $scene = :title
      $scene = nil
    end
    assert_match(/^NEXTUI_EXIT /, err)
    assert_equal 1, err.scan(/^NEXTUI_SCENE_NIL /).size
  end

  def test_orphan_return_in_proc_ends_only_that_proc
    assert_equal [:skipped, :handled], [nil, 1].map { |value| HANDLERS[0].call(value) }
    assert_equal :skipped, HANDLERS[0][nil]
    assert_equal [:done, :done], [2, 3].map { |value| HANDLERS[1].call(value) }
    assert_raises(ZeroDivisionError) { proc { 1 / 0 }.call }
  end

  def test_profiler_is_opt_in_and_writes_one_line_per_report
    Graphics.update
    refute File.exist?(File.join($HOME, 'nextui-profile.log'))
    File.write(File.join($HOME, 'nextui-profile'), '')
    NextUIProfile.start
    3.times { NextUIProfile.frame }
    NextUIProfile.report(Process.clock_gettime(Process::CLOCK_MONOTONIC))
    line = File.read(File.join($HOME, 'nextui-profile.log'))
    assert_match(/\Aframes=3 slow=\d+ longest_ms=\d+ gc_ms=\d+ major_gc=\d+ rss_mb=\d+ bitmap_gc=\d+ top=/, line)
    assert_equal 2, line.lines.size
    assert_match(/^memory bitmap_counts=.*live_pixel_bytes_est=\d+.*native_update_ms=\d+ report_ms=/, line)
    path = File.join($HOME, 'nextui-profile.log')
    File.write(path, 'x' * (256 * 1024))
    NextUIProfile.report(Process.clock_gettime(Process::CLOCK_MONOTONIC))
    refute NextUIProfile.active?
    assert_equal 256 * 1024, File.size(path)
  ensure
    NextUIProfile.stop
    File.delete(File.join($HOME, 'nextui-profile')) rescue nil
  end

  def test_allocation_telemetry_counts_animation_copies_and_actual_disposals
    NextUIBitmapTelemetry.instance_variable_set(:@counts, Hash.new(0))
    NextUIBitmapTelemetry.instance_variable_set(:@sites, Hash.new(0))
    NextUIBitmapTelemetry.instance_variable_set(:@sizes, Hash.new(0))
    NextUIProfile.instance_variable_set(:@main, Thread.current)
    bitmap = Bitmap.new(8, 8)
    bitmap.frame_count = 10
    assert_equal [2560, 10], NextUIBitmapTelemetry.estimate(bitmap)
    copy = bitmap.clone
    copy.dispose
    copy.dispose
    counts = NextUIBitmapTelemetry.instance_variable_get(:@counts)
    assert_equal 1, counts[:create]
    assert_equal 1, counts[:copy]
    assert_equal 2560, counts[:copy_bytes]
    assert_equal 1, counts[:dispose]
    assert_equal 2560, counts[:dispose_bytes]
    assert_match(/live_pixel_bytes_est=\d+/, NextUIBitmapTelemetry.summary)
    # The new diagnostics must not alter the existing GC budget for copies.
    pending = NextUIBitmapBudget.pending
    bitmap.clone
    assert_equal pending, NextUIBitmapBudget.pending
    NextUIProfile.stop
    bitmap.clone
    assert_equal 2, counts[:copy]
  ensure
    NextUIProfile.stop
  end

  def test_undisposed_bitmaps_trigger_collection
    start = NextUIBitmapBudget.collections
    Bitmap.new(1024, 1024).dispose
    11.times { Bitmap.new(1024, 1024) } # 44 MB left to the GC
    assert_equal start, NextUIBitmapBudget.collections
    Bitmap.new(1024, 1024)
    assert_equal start + 1, NextUIBitmapBudget.collections
    assert_equal 0, NextUIBitmapBudget.pending
    bitmap = Bitmap.new(10, 10)
    bitmap.dispose
    bitmap.dispose
    assert_equal 0, NextUIBitmapBudget.pending
  end

  def test_temp_folder_points_to_per_game_home
    assert_equal $HOME, ENV['TEMP']
    assert_equal $HOME, ENV['TMP']
    Dir.chdir(ENV['TEMP']) { assert_equal File.realpath($HOME), File.realpath('.') }
  end

  def test_loading_writes_no_files
    assert_empty $written
  end
end
