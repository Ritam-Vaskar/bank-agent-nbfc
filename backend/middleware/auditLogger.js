const Audit = require('../schemas/audit.schema');

async function auditLogger(req, res, next) {
  // Skip health check and static routes
  if (req.path === '/health' || req.path.startsWith('/static')) {
    return next();
  }

  const startTime = Date.now();

  // Capture original end function
  const originalEnd = res.end;

  res.end = function(...args) {
    const duration = Date.now() - startTime;

    // Log to console
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path} - ${res.statusCode} (${duration}ms)`);

    // Store audit log for important routes
    if (req.path.startsWith('/api/chat') || req.path.startsWith('/api/admin')) {
      const audit = new Audit({
        action: `${req.method} ${req.path}`,
        userId: req.user?.userId || 'anonymous',
        agent: 'system',
        metadata: {
          statusCode: res.statusCode,
          duration,
          ip: req.ip
        }
      });

      audit.save().catch(err => console.error('Audit log error:', err));
    }

    originalEnd.apply(res, args);
  };

  next();
}

module.exports = { auditLogger };
