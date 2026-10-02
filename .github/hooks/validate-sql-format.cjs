const { spawnSync } = require('node:child_process');

const chunks = [];
process.stdin.on('data', (chunk) => chunks.push(chunk));
process.stdin.on('end', () => {
  let event;
  try {
    event = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    process.exit(0);
  }

  const sqlValues = [];
  const visited = new Set();
  const sqlKeys = new Set(['query', 'sql', 'statement']);

  function collectSql(value) {
    if (!value || typeof value !== 'object' || visited.has(value)) return;
    visited.add(value);

    for (const [key, child] of Object.entries(value)) {
      if (sqlKeys.has(key.toLowerCase()) && typeof child === 'string') {
        if (/\b(select|with|insert|update|delete|create|alter|drop|truncate|explain)\b/i.test(child)) {
          sqlValues.push(child);
        }
      } else if (child && typeof child === 'object') {
        collectSql(child);
      }
    }
  }

  collectSql(event.tool_input ?? event.toolInput ?? event.toolArgs ?? event.arguments ?? event);
  if (sqlValues.length === 0) return;

  for (const sql of sqlValues) {
    const result = spawnSync('npx', ['--yes', 'sql-formatter', '--language', 'postgresql'], {
      input: sql,
      encoding: 'utf8',
      shell: true,
      timeout: 50000,
      windowsHide: true,
    });

    if (result.error || result.status !== 0) {
      deny('The PostgreSQL formatter could not process this query. Check the SQL dialect and syntax.');
      return;
    }

    const original = sql.replace(/\r\n/g, '\n').trimEnd();
    const formatted = result.stdout.replace(/\r\n/g, '\n').trimEnd();
    if (original !== formatted) {
      deny('SQL formatting check failed. Reformat the query with sql-formatter (PostgreSQL dialect) before invoking the tool.');
      return;
    }
  }
});

function deny(reason) {
  process.stdout.write(`${JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  })}\n`);
}
