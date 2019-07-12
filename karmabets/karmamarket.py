#!/usr/bin/env python3
import copy
import sqlite3 as sql
import math
#def number_shares_for_price(market, amount):
#    e = math.e
#    cost = (market.b * math.log(sum([e**(q.num_shares/market.b) for q in market.stocks]))) - (market.b * math.log(sum(


#def _find_total_cost(self, share, amount):
#    e = math.e
#    before = self.b * math.log(sum([e**(q.num_shares/self.b) for q in self.stocks]))
#    copied_stocks = self.stocks.copy()
#    copied_stocks.remove(share)
#    fake_share = copy.copy(share)
#    fake_share.num_shares += amount
#    copied_stocks.append(fake_share)
#    after = self.b * math.log(sum([e**(q.num_shares/self.b) for q in copied_stocks]))
#    return after - before
#

#TODO: make categories into objects so we can edit the judges
class _Stock:
    def __init__(self, text, market):
        self.market = market
        self.b = market.b
        self.text = text
        self.shares = {}
        self.num_shares = 0
        self.cost = 0

    @property
    def id(self):
        try:
            return self.market.marketplace.option_id_handler[self]
        except KeyError:
            return None
    def save(self):
        if not self.id and self.market.id:
            self.market.marketplace.sql_add_option(self.market, self)
        elif self.id:
            raise Exception("Stock already saved.")
        else:
            raise Exception("Market must be saved first.")
    def buy(self, player, amount):
        if not self.market.is_open:
            return
        cost = self.market._find_total_cost(self, amount)
        if player not in self.shares:
            self.shares[player] = 0
        if cost > self.market.marketplace.bank[player]:
            return
        if amount + self.shares[player] < 0:
            return
        self.market.marketplace.bank[player] -= cost
        self.num_shares += amount
        self.shares[player] += amount
        self.market._update_costs()
        self.market.marketplace._buy_share(self, player, amount)

    def __str__(self):
        return "{}\t{:.2f} [{}]".format(self.text, self.cost, self.num_shares)

    def __repr__(self):
        return "<Option {}:{}>".format(self.text, self.cost)
class _Category:
    def __init__(self, marketplace, short, long_, extra, category_id=0):
        self.marketplace = marketplace
        self.short = short
        self.long = long_
        self.extra = extra
        self.judges = []
        self.category_id = category_id
    def add_judge(self, judge):
        self.judges.append(judge)
        if self.marketplace.autosave:
            self.marketplace.sql_add_judge(self.category_id, judge)
class _Market:
    def __init__(self, marketplace, text, author, category, close_time, rules, b, comments):
        self.marketplace = marketplace
        self.text = text
        self.author = author
        self.category = category
        self.close_time = close_time
        self.rules = rules
        self.b = b
        self.comments = comments
        self.stocks = []
        self.close()

    @property
    def id(self):
        try:
            return self.marketplace.id_handler[self]
        except KeyError:
            return None
#    def save_to_db(self):
#        self.marketplace.sql_new_market(self)    
    def open(self):
        self.is_open = True
        for stock in self.stocks:
            stock.cost = 100/len(self.stocks)

    def close(self):
        self.is_open = False
    def save(self):
        if not self.id:
            self.marketplace.sql_new_market(self)
            for o in self.stocks:
                o.save()

    def add_option(self, text):
        if self.is_open:
            raise Exception("Can't add option if market is open")
        stock = _Stock(text, self)
        self.stocks.append(stock)
        for s in self.stocks:
            s.cost = self._find_current_price(s)
        if self.marketplace.autosave:
            self.marketplace.sql_add_option(self, stock)
        return stock
    def change_comments(self, comments):
        self.comments = comments
        self.marketplace._change_comments(self, comments)

    def call(self, stock):
        for player, amount in stock.shares.items():
            print("{} before: {}".format(player, self.marketplace.bank[player]))
            self.marketplace.bank[player] += amount
            self.marketplace._change_player_amount(player, self.marketplace.bank[player])
            print("{} after: {}".format(player, self.marketplace.bank[player]))
        self.marketplace._call(self)
        self.close()

    def _find_current_price(self, stock):
        e, b = math.e, self.b
        cost = e**(stock.num_shares/b) / sum([e**(q.num_shares/b) for q in self.stocks]) * 100
        return cost

    def _find_total_cost(self, share, amount):
        print(self.b)
        print(type(self.b))
        e = math.e
        before = self.b * math.log(sum([e**(q.num_shares/self.b) for q in self.stocks])) * 100
        copied_stocks = self.stocks.copy()
        copied_stocks.remove(share)
        fake_share = copy.copy(share)
        fake_share.num_shares += amount
        copied_stocks.append(fake_share)
        after = self.b * math.log(sum([e**(q.num_shares/self.b) for q in copied_stocks])) * 100
        return after - before

    def _update_costs(self):
        for stock in self.stocks:
            stock.cost = self._find_current_price(stock)
        
    def __str__(self):
        string = self.text
        label = iter("abcdefghijklmnopqrstuvwxyz")
        for s in self.stocks:
            string += "\n{}: {}".format(next(label), s)
        return string

    def __repr__(self):
        return "<Market: {}>".format(self.text)

class Marketplace:
    def __init__(self, autosave = False):
        self.autosave = False # temporarily just to add default "misc" and "Admin".
        self.con = sql.connect("karmamarket.sql")
        self.cur = self.con.cursor()
        self.markets = []
        self.categories = []
        #TODO: is this safe?
        self.bank = {"admin": 0}
        misc = _Category(self, "None", "None", "", 0)
        misc.add_judge("admin")
        misc.add_judge("sje46")
        self.categories = [misc]
        self.id_handler = {}
        self.option_id_handler = {}
        self.autosave = autosave


    def new_market(self, text, author="admin", category=None, close_time=None, rules=None, b=100, comments="", autosave=False):
        """Creates a new prediction market."""
        autosave_market = autosave
        market = _Market(self, text, author, category, close_time, rules, b, comments)
        if not category: 
            category = self.categories[0]
        if author not in category.judges:
            raise Exception("Author is not a judge in this category")
        self.markets.append(market)
        if self.autosave and not autosave_market:
            self.sql_new_market(market)
        return market

    def sql_new_market(self, market):
        text, author, rules, close_time = market.text, market.author, market.rules, market.close_time
        b, closed, comments = market.b, True, market.comments #TODO: fix closed, is_open
        self.cur.execute("""
            INSERT INTO markets
                (text, author, rules, close_time, b, closed, comments)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
            """, (text, author, rules, close_time, b, closed, comments))
        self.cur.execute("""
            SELECT last_insert_rowid()""")
        market_id = self.cur.fetchone()[0]
        self.id_handler[market] = market_id
        self.con.commit()

    def create_new_player(self, name, money):
        """Creates a new player."""
        if name in self.bank.keys():
            return
        self.bank[name] = money
        self.cur.execute("""
            INSERT INTO bank
                (name, money, in_play)
            VALUES
                (?, ?, 0)
            """, (name, money))
        self.con.commit()
    def create_new_category(self, short, long_, extra=""):
        self.cur.execute("""
            INSERT INTO categories
                (short, long, extra)
            VALUES
                (?, ?, ?)""", (short, long_, extra))
        self.cur.execute("""SELECT last_insert_rowid()""")
        result = self.cur.fetchone()[0]
        category_id = result
        category = _Category(self, short, long_, extra, category_id)
        self.categories.append(category)
        return category
    def _add_judge(self, category_id, judge):
        self.cur.execute("""
            SELECT player_id FROM bank 
            WHERE name = ?""", (judge,))
        results = self.cur.fetchone()
        player_id = results[0]
        self.cur.execute("""
            INSERT INTO judges
                (player_id, cat_id)
            VALUES (?, ?)""", (player_id, category_id))
        self.con.commit()


#    def _add_option(self, market, option):
    def sql_add_option(self, market, option):
        """Adds an option for a market to the database."""
        self.cur.execute("""
            INSERT INTO options 
                (market_id, text)
            VALUES
                (?, ?)""", (market.id, option.text))
        self.con.commit()
        self.cur.execute("""
            SELECT last_insert_rowid()""")
        result = self.cur.fetchone()[0]
        self.option_id_handler[option] = result
#        option.id = result
        return result
    def _buy_share(self, option, player, amount):
        """Records a stock being bought or sold in the database."""
        self.cur.execute("""
            SELECT player_id FROM bank 
                WHERE name = ?""", (player,))
        player_id = self.cur.fetchone()[0]
        option_id = option.id
        self.cur.execute("""
            SELECT * FROM outstanding_shares
            WHERE player_id = ? AND option_id = ?
            """, (player_id, option_id))
        result = self.cur.fetchall()
        if not result:
            
            self.cur.execute("""
                INSERT INTO outstanding_shares
                    (player_id, amount, option_id)
                VALUES
                    (?, ?, ?)
                """, (player_id, amount, option_id))
        else:
            self.cur.execute("""
                UPDATE outstanding_shares
                set amount = amount + ?
                WHERE player_id = ? AND option_id = ?
                """, (amount, player_id, option_id))

        self.con.commit()
    def _call(self, market):
##        self.cur.execute("""
##            SELECT option_id, amount, player_id FROM outstanding_shares
##            WHERE option_id = ?""", (option.id))
##        results = self.cur.fetchall()
##        for option_id, amount, player_id in results:
##            #self.cur.execute("""INSERT INTO bank""")#bgbg
##            self.cur.execute("""
##                UPDATE bank
##                set amount = ?
##                WHERE player_id = ?""", (amount, 
##
        self._delete_outstanding(market)
        self.cur.execute("UPDATE markets set closed=1 WHERE market_id=?", (market.id,))
        self.con.commit()
    def _change_player_amount(self, player, amount):
        self.cur.execute("""
            SELECT player_id FROM bank WHERE name = ?""", (player,))
        player_id = self.cur.fetchone()[0]
        self.cur.execute("""
            UPDATE bank set money = ?
            WHERE player_id = ?""", (amount, player_id))
        self.con.commit()
    def _delete_outstanding(self, market):
        """Deletes the outstanding shares in the database."""
        for stock in market.stocks:
            print("Deleting shares: {}".format(stock.id))
            self.cur.execute("""
                DELETE FROM outstanding_shares
                WHERE option_id = ?""", (stock.id,))

    def _delete_data(self):
        """Destroys the database."""
        tables = ["bank", "markets", "options", "categories", "judges", "outstanding_shares"]
        for t in tables:
            self.cur.execute("""
                DROP TABLE {}""".format(t))
        self.con.commit()
    def _change_comments(self, market, comments):
        """Updates the comments part of a market."""
        print("running _change_comments method")
        self.cur.execute("""
            UPDATE markets 
            set comments = ?
            WHERE market_id = ?
            """, (comments, market.id))
        self.con.commit()
    def _create_test_data(self):
        """Creates test data in the database."""
        self.create_new_player("sean", 5000)
        self.create_new_player("fred", 5000)
        category = self.create_new_category("USPOL", "US politics", "foo bar")
        category.judges.append("sean")
        self.cur.execute("""INSERT INTO judges (player_id, cat_id) VALUES (1, 1)""")
        president = self.new_market("Who will be president in 2020? A", category=category)
        for option in ("Vermin Supreme", "Donald Trump", "Richard Nixon's Head"):
            president.add_option(option)

    def _load(self):
        """Creates objects from database."""
        self.cur.execute("""
            SELECT * FROM categories""")
        results = self.cur.fetchall()
        for c in results:
            cat_id, short, long_, extra = c
            category = _Category(self, short, long_, extra, category_id=cat_id)
            self.categories.append(category)
        self.cur.execute("""
            SELECT * FROM markets""")
        results = self.cur.fetchall()
        for m in results:
            m_id, text, author, rules, category_id, close_time, b, closed, comments = m
            category = self.categories[0]
            for cat in self.categories:
                if cat.category_id == category_id:
                    category = cat
                    break
            loaded_market = _Market(self, text, author, category, close_time, rules, b, comments)
            loaded_market.marketplace = self
            self.id_handler[loaded_market] = m_id
#            loaded_market.id = m_id
            self.markets.append(loaded_market)
            self.cur.execute("""
                SELECT * FROM options
                WHERE market_id = ?""", (m_id,))
            option_results = self.cur.fetchall()
            for s in option_results:
                option_id, market_id, text = s
                loaded_stock = _Stock(text, loaded_market)
                self.option_id_handler[loaded_stock] = option_id
#                loaded_stock.id = option_id
                loaded_market.stocks.append(loaded_stock)
                self.cur.execute("""
                    SELECT * FROM outstanding_shares
                    WHERE option_id = ?""", (option_id,))
                shares_results = self.cur.fetchall()
                for _, amount, player_id in shares_results:
                    self.cur.execute("SELECT name FROM bank WHERE player_id = ?", (player_id,))
                    player_name = self.cur.fetchone()[0]
                    loaded_stock.num_shares += amount
                    if not player_name in loaded_stock.shares.keys():
                        loaded_stock.shares[player_name] = 0
                    loaded_stock.shares[player_name] += amount

            loaded_market._update_costs()        

                    
                    
            loaded_market.open() #TODO: need a bool column for open markets
        self.cur.execute("""
            SELECT * FROM bank""")
        results = self.cur.fetchall()
        for p in results:
            p_id, name, money, in_play = p
            self.bank[name] = money
        self.cur.execute("""
            SELECT * FROM judges""")
        results = self.cur.fetchall()
        for p in results:
            judge_id, player_id, cat_id = p
            self.cur.execute("""SELECT name FROM bank WHERE player_id=?""", (player_id,))
            players = self.cur.fetchone()
            if not players: continue
            player = players[0]
            for c in self.categories:
                if c.category_id == cat_id:
                    c.judges.append(player)
            
    def _create_new_marketplace(self):
        """Creates a karmamarket database."""
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS markets
                (market_id INTEGER PRIMARY KEY AUTOINCREMENT,
                text VARCHAR(255) NOT NULL, 
                author VARCHAR(20), 
                rules VARCHAR(255), 
                category_id INTEGER, 
                close_time INTEGER ,
                b SHORT DEFAULT 100 NOT NULL, 
                closed SHORT DEFAULT 0,
                comments VARCHAR(255), 
                FOREIGN KEY (category_id) REFERENCES categories(category_id)
                )""")
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS options
                (option_id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id INT, text VARCHAR(255),
                FOREIGN KEY (market_id) REFERENCES markets(market_id))
                """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS categories
                (category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                short VARCHAR(20) UNIQUE, long VARCHAR(255),
                extra VARCHAR(255))""")
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS bank
                (player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50), money INTEGER, in_play INTEGER)""")
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS judges
                (judge_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                player_id, cat_id, 
                FOREIGN KEY(player_id) REFERENCES bank(player_id),
                FOREIGN KEY (cat_id) REFERENCES categories(category_id))
                """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS outstanding_shares
                (option_id INTEGER, amount UNSIGNED INTEGER, player_id INTEGER,
                FOREIGN KEY (option_id) REFERENCES options(option_id),
                FOREIGN KEY (player_id) REFERENCES bank(player_id))
                """)
        self.create_new_category("MISC", "Miscellaneous")
        self.con.commit()
