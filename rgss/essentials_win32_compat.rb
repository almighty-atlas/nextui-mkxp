# SPDX-License-Identifier: MIT
# Win32API stand-in for Pokemon Essentials (v17-era) RGSS1 games under the
# H700 mkxp-z build, loaded per game through mkxp.json "preloadScript".
# Original implementation.
#
# The engine is built without MiniFFI and no Windows libraries exist on the
# device, so Essentials' `Win32API.new(dll, function, ...)` calls hit a missing
# constructor and the game aborts before its title screen. Every emulated call
# answers like an unavailable Windows API, except:
#   * window/thread identity probes, so the game finds "its" window, and
#   * GetAsyncKeyState/GetKeyState, which report the engine's own RGSS button
#     state (and therefore the reviewed gamepad bindings) for one virtual key
#     per button from Essentials' default Input.buttonToKey lists.
# It also repairs, in memory only, three Ruby 1.8 constructs that Ruby 3.1
# rejects as syntax errors (see NextUIRuby18). No native code is loaded and
# nothing outside the game's own folder is written.
module NextUIWin32
  WINDOW = 1
  THREAD = 1
  ERROR_FILE_NOT_FOUND = 2
  E_FAIL = -2147467259
  MCIERR_INVALID_DEVICE_NAME = 263
  LANG_ENGLISH_US = 0x0409

  # Windows virtual-key code => native RGSS1 buttons (captured before game
  # scripts redefine the Input constants). Exactly one key per button: the
  # game polls its key list lazily, so reporting C, Enter and Space together
  # would trigger the same press again on the following frames.
  KEYS = {
    0x28 => [Input::DOWN], 0x25 => [Input::LEFT], 0x27 => [Input::RIGHT], 0x26 => [Input::UP],
    0x0D => [Input::C],                 # Enter
    0x1B => [Input::B],                 # Esc
    0x5A => [Input::A],                 # Z (run)
    0x21 => [Input::L], 0x22 => [Input::R],  # Page Up/Down
    0x74 => [Input::F5, Input::X],      # F5: registered item, also on RGSS X
    0x10 => [Input::SHIFT], 0x11 => [Input::CTRL], 0x12 => [Input::ALT],
    0x75 => [Input::F6], 0x76 => [Input::F7], 0x77 => [Input::F8], 0x78 => [Input::F9]
  }.freeze

  # Functions whose Windows success value is non-zero (or a fixed answer).
  FIXED = {
    'GetCurrentThreadId' => THREAD, 'GetWindowThreadProcessId' => THREAD,
    'GetForegroundWindow' => WINDOW, 'GetUserDefaultLangID' => LANG_ENGLISH_US,
    'RegOpenKeyExA' => ERROR_FILE_NOT_FOUND, 'RegQueryValueExA' => ERROR_FILE_NOT_FOUND,
    'SHGetKnownFolderPath' => E_FAIL, 'SHGetSpecialFolderLocation' => E_FAIL,
    'mciSendString' => MCIERR_INVALID_DEVICE_NAME
  }.freeze

  class << Input
    alias_method :nextui_native_update, :update
    alias_method :nextui_native_press?, :press?
  end

  @frame = nil

  class << self
    def pressed?(key)
      buttons = KEYS[key]
      return false unless buttons
      # Game scripts replace Input.update, so refresh native state once a frame.
      frame = Graphics.frame_count
      unless frame == @frame
        @frame = frame
        Input.nextui_native_update
      end
      buttons.any? { |button| Input.nextui_native_press?(button) }
    end

    def call(function, args)
      case function
      when 'GetAsyncKeyState', 'GetKeyState'
        pressed?(args[0]) ? 0x8000 : 0
      when 'FindWindowEx'
        args[1] == 0 ? WINDOW : 0
      when 'GetClientRect', 'GetWindowRect'
        fill(args[1], [0, 0, Graphics.width, Graphics.height].pack('l4'))
      when 'GetSystemMetrics'
        { 0 => Graphics.width, 1 => Graphics.height }.fetch(args[0], 0)
      else
        FIXED.fetch(function, 0)
      end
    end

    # Writes a native-style result into the caller's packed buffer.
    def fill(buffer, bytes)
      return 0 unless buffer.is_a?(String) && buffer.bytesize >= bytes.bytesize
      bytes.each_byte.with_index { |byte, index| buffer.setbyte(index, byte) }
      1
    end

    # Replaces a game-defined module function as soon as the game defines it.
    def replace_when_defined(mod, name, &body)
      mod.define_singleton_method(:singleton_method_added) do |added|
        next unless added == name && !@nextui_replacing
        @nextui_replacing = true
        define_singleton_method(name, &body)
        @nextui_replacing = false
      end
    end
  end
end

class Win32API
  def initialize(_dll, function, *_signature)
    @function = function.to_s
  end

  def call(*args)
    NextUIWin32.call(@function, args)
  end
  alias Call call
end

# Ruby 1.8 core methods that RGSS1 games call and Ruby 3.1 removed (same idea
# as mkxp-z's CC0 ruby_classic_wrap.rb, plus Array#nitems). Game-defined
# methods of the same name still take precedence.
class Array
  def nitems = count { |item| !item.nil? } unless method_defined?(:nitems)
end

class Hash
  alias_method :index, :key unless method_defined?(:index)
end

class Object
  TRUE = true unless const_defined?(:TRUE)
  FALSE = false unless const_defined?(:FALSE)
  NIL = nil unless const_defined?(:NIL)
  alias_method :id, :object_id unless method_defined?(:id)
  alias_method :type, :class unless method_defined?(:type)
end

# The launcher starts the engine with an empty environment, but Essentials
# enters ENV["TEMP"] (e.g. for every GIF/empty picture). The per-game HOME
# from the launcher is the closest writable equivalent.
temp = ENV['HOME'] && File.directory?(ENV['HOME']) ? ENV['HOME'] : '.'
ENV['TEMP'] ||= temp
ENV['TMP'] ||= temp

# mkxp-z registers the game's Fonts/ folder itself; copying into a Windows
# font directory can only fail here and would prompt on every start.
module FontInstaller; end
NextUIWin32.replace_when_defined(FontInstaller, :install) { nil }

# Ruby 1.8 source that RGSS1 accepted but Ruby 3.1 refuses to parse. mkxp-z
# runs preloads after decoding $RGSS_SCRIPTS, so the decoded text (entry 3)
# can be rewritten before evaluation. Line numbers are preserved, and a
# rewrite is kept only if the script then compiles.
module NextUIRuby18
  FIXES = [
    # `when 0: # comment` => `when 0 then # comment`
    [/^([ \t]*when[ \t][^\n#]*[^:\s]):(?=[ \t]*(?:#[^\n]*)?\r?$)/, ' then'],
    # Byte escapes above 0x7F are invalid in a UTF-8 regexp.
    ['\\x7f-\\x9f]', '\\x7f\\u0080-\\u009f]'],
    # `x=0.` + newline turns the next keyword into a method call.
    [/(=[ \t]*\d+)\.(?=[ \t]*\r?\n[ \t]*(?:end|elsif|else|when)\b)/, '']
  ].freeze

  def self.repair(source)
    # Scripts with invalid UTF-8 (in comments or strings) still parse as is.
    return source unless source.valid_encoding?
    fixed = FIXES.reduce(source) { |text, (pattern, replacement)| text.gsub(pattern) { $1 ? $1 + replacement : replacement } }
    return source if fixed == source
    RubyVM::InstructionSequence.compile(fixed)
    fixed
  rescue SyntaxError
    source
  end

  def self.repair_scripts(scripts)
    count = 0
    scripts.each do |script|
      next unless script.is_a?(Array) && script[3].is_a?(String)
      fixed = repair(script[3])
      next if fixed.equal?(script[3])
      script[3] = fixed
      count += 1
    end
    count
  end
end
NextUIRuby18.repair_scripts($RGSS_SCRIPTS) if $RGSS_SCRIPTS.is_a?(Array)
