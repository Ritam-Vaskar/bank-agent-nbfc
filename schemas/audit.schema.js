const mongoose = require('mongoose');

const auditSchema = new mongoose.Schema({
  loanId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Loan'
  },
  userId: {
    type: String,
    required: true
  },
  agent: {
    type: String,
    required: true
  },
  action: {
    type: String,
    required: true
  },
  timestamp: {
    type: Date,
    default: Date.now,
    immutable: true
  },
  metadata: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  }
});

// Make audit logs immutable
auditSchema.pre('save', function(next) {
  if (!this.isNew) {
    return next(new Error('Audit logs cannot be modified'));
  }
  next();
});

module.exports = mongoose.model('Audit', auditSchema);
