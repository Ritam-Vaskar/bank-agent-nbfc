const express = require('express');
const auth = require('../middleware/auth');
const Loan = require('../schemas/loan.schema');
const User = require('../schemas/user.schema');
const Audit = require('../schemas/audit.schema');

const router = express.Router();

// Admin only middleware
const adminOnly = (req, res, next) => {
  if (req.user.role !== 'admin') {
    return res.status(403).json({
      success: false,
      message: 'Admin access required'
    });
  }
  next();
};

// Get all loans
router.get('/loans', auth, adminOnly, async (req, res) => {
  try {
    const { state, riskLevel, page = 1, limit = 20 } = req.query;

    const filter = {};
    if (state) filter.state = state;
    if (riskLevel) filter.riskLevel = riskLevel;

    const loans = await Loan.find(filter)
      .sort({ createdAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit)
      .populate('userId', 'name email');

    const count = await Loan.countDocuments(filter);

    res.json({
      success: true,
      loans,
      totalPages: Math.ceil(count / limit),
      currentPage: page
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

// Get all users
router.get('/users', auth, adminOnly, async (req, res) => {
  try {
    const users = await User.find().select('-password');
    res.json({
      success: true,
      users
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

// Get audit logs
router.get('/audit', auth, adminOnly, async (req, res) => {
  try {
    const { loanId, page = 1, limit = 50 } = req.query;

    const filter = loanId ? { loanId } : {};

    const audits = await Audit.find(filter)
      .sort({ timestamp: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit);

    const count = await Audit.countDocuments(filter);

    res.json({
      success: true,
      audits,
      totalPages: Math.ceil(count / limit),
      currentPage: page
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

// Get dashboard stats
router.get('/stats', auth, adminOnly, async (req, res) => {
  try {
    const totalLoans = await Loan.countDocuments();
    const activeLoans = await Loan.countDocuments({ state: { $ne: 'COMPLETE' } });
    const completedLoans = await Loan.countDocuments({ state: 'COMPLETE' });
    const totalUsers = await User.countDocuments();

    const riskDistribution = await Loan.aggregate([
      { $group: { _id: '$riskLevel', count: { $sum: 1 } } }
    ]);

    const stateDistribution = await Loan.aggregate([
      { $group: { _id: '$state', count: { $sum: 1 } } }
    ]);

    res.json({
      success: true,
      stats: {
        totalLoans,
        activeLoans,
        completedLoans,
        totalUsers,
        riskDistribution,
        stateDistribution
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

// Update loan state (manual override)
router.patch('/loans/:loanId', auth, adminOnly, async (req, res) => {
  try {
    const { state, riskLevel, notes } = req.body;

    const loan = await Loan.findById(req.params.loanId);
    if (!loan) {
      return res.status(404).json({
        success: false,
        message: 'Loan not found'
      });
    }

    if (state) loan.state = state;
    if (riskLevel) loan.riskLevel = riskLevel;

    await loan.save();

    // Log audit
    const audit = new Audit({
      loanId: loan._id,
      agent: 'admin',
      action: `Manual update: ${notes || 'State changed'}`,
      userId: req.user.userId
    });
    await audit.save();

    res.json({
      success: true,
      loan
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

module.exports = router;
