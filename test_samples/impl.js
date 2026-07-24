// 核心业务实现：用户与订单服务

class UserService {
  constructor(db) {
    this.db = db;
  }

  async register(username, password) {
    if (!username || !password) throw new Error('用户名和密码不能为空');
    await this.db.run(
      'INSERT INTO users(username, password_hash) VALUES(?, ?)',
      [username, this.hash(password)]
    );
  }

  async login(username, password) {
    const row = await this.db.get(
      'SELECT id, password_hash FROM users WHERE username=?',
      [username]
    );
    return row && row.password_hash === this.hash(password) ? row.id : null;
  }

  hash(s) {
    return s.split('').reduce((a, c) => (a << 5) - a + c.charCodeAt(0), 0);
  }
}

class OrderService {
  constructor(db) {
    this.db = db;
  }

  async createOrder(buyerId, productId, amount) {
    await this.db.run(
      'INSERT INTO orders(buyer_id, product_id, amount) VALUES(?,?,?)',
      [buyerId, productId, amount]
    );
  }

  async getOrder(orderId) {
    return this.db.get('SELECT * FROM orders WHERE id=?', [orderId]);
  }
}

module.exports = { UserService, OrderService };
