/*
 * A very small reader and writer for zip files, using only Node's own zlib.
 *
 * Playwright saves a trace as a zip file and has no setting to remove secrets from it. To take
 * them out, the trace has to be opened, changed and closed again. Node has no zip support of its
 * own, and this quest adds no package, so the little that is needed is here: read every entry of
 * a zip, and write a list of entries as a zip.
 *
 * It handles what Playwright's traces use: entries stored or deflated, no encryption, no zip64.
 * Anything else is refused with an error, never guessed at.
 *
 * Used by support/evidence.ts (inside Playwright) and by tools/failure-evidence-check.ts (plain
 * Node), so it uses only syntax that Node can run as it is.
 */

import { crc32, deflateRawSync, inflateRawSync } from "node:zlib";

export type ZipEntry = { name: string; data: Buffer };

export function readZip(file: Buffer): ZipEntry[] {
  let end = -1;
  for (let at = file.length - 22; at >= 0 && at >= file.length - 22 - 65535; at -= 1) {
    if (file.readUInt32LE(at) === 0x06054b50) {
      end = at;
      break;
    }
  }
  if (end < 0) throw new Error("not a zip file: no end record");
  const count = file.readUInt16LE(end + 10);
  let at = file.readUInt32LE(end + 16);
  if (count === 0xffff || at === 0xffffffff) throw new Error("zip64 files are not supported");
  const entries: ZipEntry[] = [];
  for (let n = 0; n < count; n += 1) {
    if (file.readUInt32LE(at) !== 0x02014b50) throw new Error("damaged zip file: bad directory entry");
    const flags = file.readUInt16LE(at + 8);
    const method = file.readUInt16LE(at + 10);
    const crc = file.readUInt32LE(at + 16);
    const packed = file.readUInt32LE(at + 20);
    const size = file.readUInt32LE(at + 24);
    const nameLength = file.readUInt16LE(at + 28);
    const extraLength = file.readUInt16LE(at + 30);
    const commentLength = file.readUInt16LE(at + 32);
    const local = file.readUInt32LE(at + 42);
    const name = file.subarray(at + 46, at + 46 + nameLength).toString("utf8");
    if (flags & 1) throw new Error(`encrypted entry: ${name}`);
    if (file.readUInt32LE(local) !== 0x04034b50) throw new Error(`damaged zip file: bad header for ${name}`);
    const start = local + 30 + file.readUInt16LE(local + 26) + file.readUInt16LE(local + 28);
    const raw = file.subarray(start, start + packed);
    let data: Buffer;
    if (method === 0) data = Buffer.from(raw);
    else if (method === 8) data = inflateRawSync(raw);
    else throw new Error(`unsupported compression ${method} for ${name}`);
    if (data.length !== size || crc32(data) !== crc) throw new Error(`damaged zip file: ${name} does not match its checksum`);
    entries.push({ name, data });
    at += 46 + nameLength + extraLength + commentLength;
  }
  return entries;
}

export function writeZip(entries: ZipEntry[]): Buffer {
  const parts: Buffer[] = [];
  const directory: Buffer[] = [];
  let offset = 0;
  for (const entry of entries) {
    const name = Buffer.from(entry.name, "utf8");
    const packed = deflateRawSync(entry.data);
    const crc = crc32(entry.data);
    const header = Buffer.alloc(30);
    header.writeUInt32LE(0x04034b50, 0);
    header.writeUInt16LE(20, 4);            // version needed
    header.writeUInt16LE(0x0800, 6);        // names are UTF-8
    header.writeUInt16LE(8, 8);             // deflated
    header.writeUInt16LE(0, 10);            // time: midnight
    header.writeUInt16LE(0x0021, 12);       // date: 1980-01-01, so the file does not say when it was made
    header.writeUInt32LE(crc, 14);
    header.writeUInt32LE(packed.length, 18);
    header.writeUInt32LE(entry.data.length, 22);
    header.writeUInt16LE(name.length, 26);
    header.writeUInt16LE(0, 28);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    header.copy(central, 6, 4, 30);         // the same fields, from "version needed" to "extra length"
    central.writeUInt32LE(offset, 42);
    parts.push(header, name, packed);
    directory.push(central, name);
    offset += header.length + name.length + packed.length;
  }
  const directorySize = directory.reduce((sum, part) => sum + part.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(directorySize, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...parts, ...directory, end]);
}

/** True for content that is not text: a picture, a font. Such an entry is kept as it is and cannot be searched line by line. */
export function looksBinary(data: Buffer): boolean {
  return data.subarray(0, 4096).includes(0);
}
