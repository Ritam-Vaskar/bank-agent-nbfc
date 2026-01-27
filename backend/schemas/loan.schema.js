const mongoose = require('mongoose');

const loanSchema = new mongoose.Schema({
  userId: {
    type: String,
    required: true,
    index: true
  },
  state: {
    type: String,
    enum: ['INIT', 'SALES', 'KYC', 'CREDIT', 'DOCUMENTS', 'OFFER', 'ACCEPTANCE', 'SANCTION', 'COMPLETE'],
    default: 'INIT',
    required: true
  },
  data: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  },
  riskLevel: {
    type: String,
    enum: ['LOW', 'MEDIUM', 'HIGH', null],
    default: null
  },
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
});

loanSchema.pre('save', function(next) {
  this.updatedAt = Date.now();
  next();
});

module.exports = mongoose.model('Loan', loanSchema);
