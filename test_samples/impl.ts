// 核心业务实现：用户与订单服务（TypeScript）

interface User { id: number; username: string; passwordHash: number; }
interface Order { id: number; buyerId: number; productId: number; amount: number; }

class UserService {
  constructor(private db: any) {}

  async register(username: string, password: string): Promise<void> {
    if (!username || !password) throw new Error('用户名和密码不能为空');
    await this.db.run(
      'INSERT INTO users(username, password_hash) VALUES(?, ?)',
      [username, this.hash(password)]
    );
  }

  async login(username: string, password: string): Promise<number | null> {
    const row = await this.db.get(
      'SELECT id, password_hash FROM users WHERE username=?',
      [username]
    );
    return row && row.password_hash === this.hash(password) ? row.id : null;
  }

  private hash(s: string): number {
    return s.split('').reduce((a, c) => (a << 5) - a + c.charCodeAt(0), 0);
  }
}

class OrderService {
  constructor(private db: any) {}

  async createOrder(buyerId: number, productId: number, amount: number): Promise<void> {
    await this.db.run(
      'INSERT INTO orders(buyer_id, product_id, amount) VALUES(?,?,?)',
      [buyerId, productId, amount]
    );
  }

  async getOrder(orderId: number): Promise<Order | null> {
    return this.db.get('SELECT * FROM orders WHERE id=?', [orderId]);
  }
}

export { UserService, OrderService };
