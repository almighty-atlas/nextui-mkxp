# SPDX-License-Identifier: MIT
# Original, asset-free extension-completeness tests. No game/firmware changes.
require 'timeout'

STDOUT.sync = true
abort 'UNEXPECTED_RUBY_VERSION' unless RUBY_VERSION == '3.1.3'
abort 'UNEXPECTED_PLATFORM' unless RUBY_PLATFORM == ARGV.fetch(0)
puts "RUNTIME ruby=#{RUBY_VERSION} platform=#{RUBY_PLATFORM}"

def check(name)
  Timeout.timeout(5) { yield }
  puts "PASS #{name}"
rescue Exception => error
  warn "FAIL #{name} #{error.class}: #{error.message}"
  exit 1
end

def assert(value)
  raise 'assertion failed' unless value
end

check('stdlib_stringio_date_set_shellwords') do
  %w[stringio date set shellwords].each { |name| require name }
  assert(StringIO.new('test').read == 'test')
  assert(Date.iso8601('2026-10-28') == Date.new(2026, 10, 28))
  assert(Set.new([1, 1, 2]).size == 2)
  assert(Shellwords.split('"path with spaces" test') == ['path with spaces', 'test'])
end

check('encoding_transcoder_roundtrips') do
  require 'enc/encdb'
  require 'enc/trans/transdb'
  text = "Gr\u00fc\u00dfe"
  %w[UTF-16LE UTF-16BE UTF-32LE UTF-32BE ISO-8859-1].each do |name|
    encoding = Encoding.find(name)
    assert(text.encode(encoding).encode('UTF-8') == text)
  end
  assert("\u3042".encode('Windows-31J').encode('UTF-8') == "\u3042")
end

check('psych_safe_load_dump_roundtrip') do
  require 'psych'
  data = { 'answer' => 42, 'flags' => [true, nil, false], 'word' => "Gr\u00fc\u00dfe" }
  assert(Psych.safe_load(Psych.dump(data)) == data)
  assert(Psych.safe_load("--- 2026-10-28\n", permitted_classes: [Date]) == Date.new(2026, 10, 28))
end

check('psych_rejects_objects_and_aliases') do
  rejected = false
  begin
    Psych.safe_load("--- !ruby/object:Object {}\n")
  rescue Psych::DisallowedClass
    rejected = true
  end
  assert(rejected)
  rejected = false
  begin
    Psych.safe_load("---\na: &anchor [1]\nb: *anchor\n")
  rescue Psych::BadAlias
    rejected = true
  end
  assert(rejected)
end

check('fiddle_libc_strlen_allocation_free') do
  require 'fiddle'
  libc = Fiddle.dlopen(ARGV.fetch(1))
  strlen = Fiddle::Function.new(libc['strlen'], [Fiddle::TYPE_VOIDP], Fiddle::TYPE_SIZE_T)
  address = Fiddle.malloc(16)
  begin
    pointer = Fiddle::Pointer.new(address, 16)
    pointer[0, 5] = "H700\0"
    assert(strlen.call(pointer) == 4)
  ensure
    Fiddle.free(address)
  end
  libc.close
end

loaded = $LOADED_FEATURES.grep(/\.so\z/).map { |path| File.basename(path) }.sort
puts "LOADED_EXTENSIONS #{loaded.join(',')}"
if File.readable?('/proc/self/maps')
  maps = File.read('/proc/self/maps').lines.filter_map do |line|
    path = line.split.last
    File.basename(path) if path && path.start_with?('/') && path.include?('.so')
  end
  puts "MAPPED_LIBRARIES #{maps.uniq.sort.join(',')}"
end
puts 'RUBY_RUNTIME_BATCH_PASS'
