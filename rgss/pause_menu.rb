# SPDX-License-Identifier: MIT
# NextUI H700 pause menu for RGSS1 games under mkxp-z, loaded through the
# per-game mkxp.json "preloadScript" list. Original implementation.
#
# The Menu button is read passively from evdev (no grab, no writes), so SDL
# and NextUI keep receiving it. Save and Load open the game's own screens;
# there are no emulator-style save states.
module NextUIPause
  KEY_CODE = 312 # Menu button on event1, observed on NextUI-20261013-0 (314 is L2)
  DEVICE_NAMES = ['ANBERNIC-keys'].freeze
  EVENT = 'q<q<S<S<l<' # struct input_event on aarch64
  EVENT_SIZE = 24
  ITEMS = ['Continue', 'Save', 'Load', 'Quit'].freeze

  @io = nil
  @attached = false
  @active = false
  @disabled = false

  class << self
    def find_device(listing = '/proc/bus/input/devices')
      File.read(listing).split(/\n\s*\n/).each do |block|
        name = block[/^N: Name="([^"]*)"/, 1]
        node = block[/^H: Handlers=.*\b(event\d+)\b/, 1]
        return "/dev/input/#{node}" if node && DEVICE_NAMES.include?(name)
      end
      nil
    rescue SystemCallError, IOError
      nil
    end

    def use_input(io)
      @io = io
      @attached = true
    end

    def input
      unless @attached
        @attached = true
        path = find_device
        begin
          @io = path && File.open(path, File::RDONLY | File::NONBLOCK)
        rescue SystemCallError, IOError
          @io = nil
        end
      end
      @io
    end

    # Drain pending events; true when the Menu button was freshly pressed.
    def menu_pressed?
      io = input
      return false unless io
      hit = false
      64.times do
        data = io.read_nonblock(EVENT_SIZE * 32, exception: false)
        break if data == :wait_readable
        if data.nil?
          detach
          break
        end
        (data.bytesize / EVENT_SIZE).times do |i|
          _, _, type, code, value = data.unpack(EVENT, offset: i * EVENT_SIZE)
          hit = true if type == 1 && code == KEY_CODE && value == 1
        end
      end
      hit
    rescue IOError, SystemCallError
      detach
      false
    end

    def detach
      @io.close if @io && !@io.closed?
    rescue IOError
      nil
    ensure
      @io = nil
    end

    def poll
      return if @active || @disabled
      open_menu if menu_pressed?
    rescue StandardError => e
      # Never let the overlay break the game: report once, then stay off.
      @disabled = true
      $stderr.puts "NEXTUI_PAUSE_ERROR=#{e.class}"
    end

    def open_menu
      @active = true
      frames = Graphics.frame_count
      choice = choose(ITEMS, [true, can_save?, can_load?, true])
      choice = nil if choice == 3 && choose(['Cancel', 'Quit game'], [true, true]) != 1
      wait_for_release
      Graphics.frame_count = frames # pausing does not count as play time
      perform(choice)
    ensure
      @active = false
    end

    def map_idle?
      return false unless defined?(Scene_Map) && $scene.is_a?(Scene_Map)
      return false unless $game_system && $game_temp
      !$game_system.map_interpreter.running? && !$game_temp.message_window_showing
    rescue NoMethodError
      false
    end

    def can_save?
      map_idle? && !!defined?(Scene_Save) && !$game_system.save_disabled
    end

    def can_load?
      map_idle? && !!defined?(Scene_Load) && (1..4).any? { |i| File.exist?("Save#{i}.rxdata") }
    end

    def perform(choice)
      case choice
      when 1
        # Same path as the "Call Save Screen" event command; Scene_Map returns to the map.
        $game_temp.save_calling = true
        $scene = Scene_Save.new unless $scene.respond_to?(:call_save, true)
      when 2 then open_load
      when 3
        %i[bgm_fade bgs_fade me_fade].each { |fade| Audio.send(fade, 800) }
        $scene = nil # the default Main loop ends and mkxp-z shuts down normally
      end
    end

    def open_load
      previous = $game_temp
      scene = Scene_Load.new # resets $game_temp; keep the map's until it starts
      fresh = $game_temp
      $game_temp = previous
      scene.define_singleton_method(:main) do
        $game_temp = fresh
        super()
      end
      scene.define_singleton_method(:on_cancel) do |*|
        NextUIPause.sound(:cancel)
        $game_temp = previous
        $scene = Scene_Map.new # instead of the title screen
      end
      $scene = scene
    end

    def sound(kind)
      $game_system.se_play($data_system.send("#{kind}_se")) if $game_system && $data_system
    rescue NoMethodError
      nil
    end

    def choose(items, enabled, index = 0)
      build(items.size)
      draw(items, enabled, index)
      loop do
        Graphics.update
        Input.nextui_pause_original_update
        return nil if menu_pressed? || Input.trigger?(Input::B)
        step = Input.repeat?(Input::DOWN) ? 1 : Input.repeat?(Input::UP) ? -1 : 0
        if step != 0
          index = (index + step) % items.size
          sound(:cursor)
          draw(items, enabled, index)
        elsif Input.trigger?(Input::C)
          next sound(:buzzer) unless enabled[index]
          sound(:decision)
          return index
        end
      end
    ensure
      dispose
    end

    def build(count)
      width = Graphics.width rescue 640
      height = Graphics.height rescue 480
      @viewport = Viewport.new(0, 0, width, height)
      @viewport.z = 10_000
      @shade = Sprite.new(@viewport)
      @shade.bitmap = Bitmap.new(width, height)
      @shade.bitmap.fill_rect(0, 0, width, height, Color.new(0, 0, 0, 150))
      @panel = Sprite.new(@viewport)
      @panel.bitmap = Bitmap.new(220, 24 + count * 32)
      @panel.x = (width - 220) / 2
      @panel.y = (height - @panel.bitmap.height) / 2
    end

    def draw(items, enabled, index)
      bitmap = @panel.bitmap
      bitmap.clear
      bitmap.fill_rect(0, 0, bitmap.width, bitmap.height, Color.new(16, 16, 32, 230))
      items.each_with_index do |label, i|
        y = 12 + i * 32
        bitmap.fill_rect(8, y, bitmap.width - 16, 32, Color.new(255, 255, 255, 70)) if i == index
        bitmap.font.color = enabled[i] ? Color.new(255, 255, 255) : Color.new(128, 128, 128)
        bitmap.draw_text(0, y, bitmap.width, 32, label, 1)
      end
    end

    def dispose
      [@panel, @shade].compact.each do |sprite|
        sprite.bitmap.dispose if sprite.bitmap
        sprite.dispose
      end
      @viewport.dispose if @viewport
      @panel = @shade = @viewport = nil
    end

    # Keep the confirming/cancelling press from reaching the game's own scene.
    def wait_for_release
      60.times do
        break unless Input.press?(Input::C) || Input.press?(Input::B)
        Graphics.update
        Input.nextui_pause_original_update
      end
      Input.nextui_pause_original_update
    end
  end
end

unless Input.respond_to?(:nextui_pause_original_update)
  class << Input
    alias_method :nextui_pause_original_update, :update

    def update
      nextui_pause_original_update
      NextUIPause.poll
    end
  end
end
