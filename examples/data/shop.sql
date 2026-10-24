CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT, signup_date TEXT);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), order_date TEXT);
CREATE TABLE order_items (order_id INTEGER REFERENCES orders(id), product_id INTEGER REFERENCES products(id), quantity INTEGER);
INSERT INTO customers VALUES (1,'Asha Rao','India','2026-01-14'),(2,'Ben Carter','USA','2026-02-03'),(3,'Chloe Martin','France','2026-02-20'),(4,'Diego Lopez','Mexico','2026-03-11'),(5,'Emi Sato','Japan','2026-04-02'),(6,'Farah Khan','India','2026-05-19');
INSERT INTO products VALUES (1,'Trail Runner','Shoes',129.0),(2,'City Sneaker','Shoes',89.0),(3,'Rain Shell','Jackets',159.0),(4,'Down Vest','Jackets',119.0),(5,'Merino Tee','Tops',49.0),(6,'Running Cap','Accessories',25.0);
INSERT INTO orders VALUES (1,1,'2026-06-02'),(2,2,'2026-06-05'),(3,1,'2026-06-20'),(4,3,'2026-07-01'),(5,4,'2026-07-08'),(6,5,'2026-07-15'),(7,2,'2026-08-01'),(8,6,'2026-08-09'),(9,6,'2026-08-30'),(10,3,'2026-09-04');
INSERT INTO order_items VALUES (1,1,1),(1,5,2),(2,2,1),(3,3,1),(4,5,3),(4,6,1),(5,1,2),(6,4,1),(6,5,1),(7,3,1),(7,6,2),(8,2,2),(9,1,1),(9,3,1),(10,4,1);
