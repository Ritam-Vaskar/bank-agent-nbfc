const bcrypt = require('bcryptjs');

// Demo users to seed the database
const demoUsers = [
  {
    name: 'Demo User',
    email: 'demo@example.com',
    password: 'demo123',
    role: 'user'
  },
  {
    name: 'Admin User',
    email: 'admin@example.com',
    password: 'admin123',
    role: 'admin'
  },
  {
    name: 'John Doe',
    email: 'john@example.com',
    password: 'password123',
    role: 'user'
  }
];

async function seedUsers() {
  const mongoose = require('mongoose');
  const User = require('../schemas/user.schema');

  try {
    await mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/bank_agent');

    console.log('🌱 Seeding demo users...');

    for (const userData of demoUsers) {
      const existingUser = await User.findOne({ email: userData.email });

      if (!existingUser) {
        const hashedPassword = await bcrypt.hash(userData.password, 10);
        
        const user = new User({
          ...userData,
          password: hashedPassword
        });

        await user.save();
        console.log(`✅ Created user: ${userData.email}`);
      } else {
        console.log(`⏭️  User already exists: ${userData.email}`);
      }
    }

    console.log('✅ Seeding complete!');
    process.exit(0);
  } catch (error) {
    console.error('❌ Seeding error:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  seedUsers();
}

module.exports = { demoUsers, seedUsers };
