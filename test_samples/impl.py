"""核心业务实现：用户与订单服务"""


class UserService:
    """用户服务：注册、登录、查询"""

    def __init__(self, db):
        self.db = db

    def register(self, username, password):
        if not username or not password:
            raise ValueError("用户名和密码不能为空")
        self.db.execute(
            "INSERT INTO users(username, password_hash) VALUES(?, ?)",
            (username, hash(password))
        )

    def login(self, username, password):
        row = self.db.query_one(
            "SELECT id, password_hash FROM users WHERE username=?",
            (username,)
        )
        if row and row["password_hash"] == hash(password):
            return row["id"]
        return None


class OrderService:
    """订单服务：下单、查询"""

    def __init__(self, db):
        self.db = db

    def create_order(self, buyer_id, product_id, amount):
        self.db.execute(
            "INSERT INTO orders(buyer_id, product_id, amount) VALUES(?,?,?)",
            (buyer_id, product_id, amount)
        )

    def get_order(self, order_id):
        return self.db.query_one(
            "SELECT * FROM orders WHERE id=?", (order_id,)
        )
