const fs = require('node:fs');
const path = require('node:path');

const chunks = [];
process.stdin.on('data', (chunk) => chunks.push(chunk));
process.stdin.on('end', () => {
  let event = {};
  try {
    event = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    event = {};
  }

  const rawError = event.error ?? event.error_message ?? event.errorMessage ?? event.message;
  const message = typeof rawError === 'string'
    ? rawError
    : rawError && typeof rawError.message === 'string'
      ? rawError.message
      : 'Unspecified agent error';
  const safeMessage = message
    .replace(/\bBearer\s+\S+/gi, 'Bearer [REDACTED]')
    .replace(/(api[_-]?key|password|secret|token)\s*[:=]\s*["']?[^\s,"']+/gi, '$1=[REDACTED]')
    .replace(/[\r\n\t]+/g, ' ')
    .slice(0, 1000);
  const record = {
    timestamp: new Date().toISOString(),
    tool: event.tool_name ?? event.toolName ?? 'unknown',
    error: safeMessage,
  };

  const logPath = path.resolve(__dirname, '..', '..', 'agent-errors.log');
  fs.appendFileSync(logPath, `${JSON.stringify(record)}\n`, 'utf8');
});
