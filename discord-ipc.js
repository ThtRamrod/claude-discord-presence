// Minimal Discord Rich Presence client over the local IPC pipe — no dependencies.
// Frame format: int32 LE opcode, int32 LE length, JSON payload.

const net = require('net');
const crypto = require('crypto');
const { EventEmitter } = require('events');

const OP_HANDSHAKE = 0;
const OP_FRAME = 1;
const OP_CLOSE = 2;
const OP_PING = 3;
const OP_PONG = 4;

function pipePath(i) {
  if (process.platform === 'win32') return `\\\\?\\pipe\\discord-ipc-${i}`;
  const tmp = process.env.XDG_RUNTIME_DIR || process.env.TMPDIR || process.env.TMP || process.env.TEMP || '/tmp';
  return `${tmp.replace(/\/$/, '')}/discord-ipc-${i}`;
}

function encode(op, data) {
  const json = Buffer.from(JSON.stringify(data), 'utf8');
  const header = Buffer.alloc(8);
  header.writeInt32LE(op, 0);
  header.writeInt32LE(json.length, 4);
  return Buffer.concat([header, json]);
}

function tryConnect(i) {
  return new Promise((resolve, reject) => {
    const sock = net.createConnection(pipePath(i));
    sock.once('connect', () => resolve(sock));
    sock.once('error', reject);
  });
}

class DiscordIPC extends EventEmitter {
  constructor(clientId) {
    super();
    this.clientId = clientId;
    this.sock = null;
    this.buffer = Buffer.alloc(0);
  }

  async connect() {
    let sock = null;
    for (let i = 0; i < 10 && !sock; i++) {
      try {
        sock = await tryConnect(i);
      } catch {
        // try next pipe
      }
    }
    if (!sock) throw new Error('Discord is not running (no IPC pipe found)');

    this.sock = sock;
    sock.on('data', (chunk) => this._onData(chunk));
    sock.on('close', () => {
      this.sock = null;
      this.emit('close');
    });
    sock.on('error', () => {});

    return new Promise((resolve, reject) => {
      const onReady = () => {
        this.off('error', onError);
        resolve();
      };
      const onError = (err) => {
        this.off('ready', onReady);
        reject(err);
      };
      this.once('ready', onReady);
      this.once('error', onError);
      sock.write(encode(OP_HANDSHAKE, { v: 1, client_id: this.clientId }));
    });
  }

  _onData(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    while (this.buffer.length >= 8) {
      const op = this.buffer.readInt32LE(0);
      const len = this.buffer.readInt32LE(4);
      if (this.buffer.length < 8 + len) break;
      const payload = JSON.parse(this.buffer.subarray(8, 8 + len).toString('utf8'));
      this.buffer = this.buffer.subarray(8 + len);

      if (op === OP_PING) {
        this.sock.write(encode(OP_PONG, payload));
      } else if (op === OP_CLOSE) {
        this.emit('error', new Error(payload.message || 'Discord closed the connection'));
        this.sock.destroy();
      } else if (op === OP_FRAME) {
        if (payload.evt === 'READY') this.emit('ready', payload.data);
        else if (payload.evt === 'ERROR') this.emit('error', new Error(payload.data && payload.data.message));
      }
    }
  }

  setActivity(activity) {
    if (!this.sock) return;
    this.sock.write(
      encode(OP_FRAME, {
        cmd: 'SET_ACTIVITY',
        args: { pid: process.pid, activity },
        nonce: crypto.randomUUID(),
      })
    );
  }

  close() {
    if (this.sock) this.sock.end();
  }
}

module.exports = { DiscordIPC };
