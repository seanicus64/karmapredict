#!/usr/bin/env python3
import copy
import sqlite3 as sql
import math

class _Stock:
    """An option for a market. You can buy and sell these but the price will change."""
    def __init__(self, text, market):
        self.market = market
        self.b = market.b
        self.text = text
        self.shares = {}
        self.num_shares = 0
        self.cost = 0
        self._open = None
        self._close = None
        self._high = None
        self._low = None
        self.volume = 0
    @property
    def open(self):
        "Cost of share at beginning of a trading day."
        return self._open
    @property
    def close(self):
        "Cost of share at end of a trading day."
        return self._close
    @property
    def high(self):
        "Highest cost (so far) of a share during a trading day."
        return self._high
    @property
    def low(self):
        "Lowest cost (so far) of a share during a trading day."
        return self._low
    @high.setter
    def high(self, value):
        "Sets _high value."
        if not self._high:
            self._high = value
        elif value > self._high:
            self._high = value

    @low.setter
    def low(self, value):
        "Sets _low value."
        if not self._low:
            self._low = value
        elif value < self._low:
            self._low = value

    @property
    def id(self):
        """Grabs the id for the share from the database.  Only works if market is
        saved to the database."""
        try:
            return self.market.marketplace.option_id_handler[self]
        except KeyError:
            return None

    def update_candle(self):
        "If current cost is lowest or highest so far, updates _low or _high value."
        self.low = self.cost
        self.high = self.cost
            
    def save(self):
        "Saves the option to database, assigning an id in the process."
        if not self.id and self.market.id:
            self.market.marketplace.sql_add_option(self.market, self)
        elif self.id:
            raise Exception("Stock already saved.")
        else:
            raise Exception("Market must be saved first.")

    def buy(self, player, amount):
        "Handles a player buying a share. If amount is negative, they're selling."
        if not self.market.is_open:
            return
            
        cost = self.market._find_total_cost(self, amount)
        if player not in self.shares:
            self.shares[player] = 0
            self.shares[player] = {"amount": 0, "cost": 0}
        #TODO: amount is going below 0
        if cost > self.market.marketplace.bank[player]:
            return
        if amount + self.shares[player]["amount"] < 0:
            # prevents player from selling more than they have.
            return
            
        self.market.marketplace.bank[player] -= cost
        self.num_shares += amount
        # volume is the total amount of stocks moved (sold or bought) in the trading day.
        self.volume += abs(amount)
        self.shares[player]["amount"] += amount
        self.shares[player]["cost"] += cost
        self.market._update_costs()

        if self.id:
            # These all are sql functions and thus can't work if market and options aren't saved.
            self.market.marketplace._buy_share(self, player, amount, cost)
            for stock in self.market.stocks:
                self.market.marketplace.sql_update_candle(stock)

            self.market.marketplace._change_player_amount(player, self.market.marketplace.bank[player])

    def __str__(self):
        return "{}\t{:.2f} [{}]".format(self.text, self.cost, self.num_shares)

    def __repr__(self):
        return "<Option {}:{}>".format(self.text, self.cost)

class _Category:
    "A collection of markets controlled by a list of judges who will decide settlements."
    def __init__(self, marketplace, short, long_, extra, category_id=0):
        self.marketplace = marketplace
        self.short = short # shorthand name, e.g. "USPOL"
        self.long = long_ # longhand name, e.g. "U.S. Politics"
        self.extra = extra # Any additional community information that user wants to store in database
        self.judges = []
        self.category_id = category_id
    def add_judge(self, judge):
        "Adds a judge."
        self.judges.append(judge)
        if self.marketplace.autosave:
            self.marketplace.sql_add_judge(self.category_id, judge)

class _Market:
    """A general inquiry of which multiple prediction are available to be bought or sold based off
    perceived liklihood."""
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
        "The ID, defined by the database, only works if market is saved."
        try:
            return self.marketplace.id_handler[self]
        except KeyError:
            return None

    def open(self):
        "Opens the market for buying/selling shares."
        self.is_open = True
        for stock in self.stocks:
            # Default cost of all options must add up to 100
            stock.cost = 100/len(self.stocks)
        self.new_candle()
    def reopen(self):
        self.is_open = True
        self._update_costs()
        for option in self.stocks:
            results = self.marketplace.sql_get_history(option, 1)
            if not results:
                self.new_candle()
            else:
                option_id, date, open_, high, low, close, volume = results[0]
                option._open = open_
                option._high = high
                option._low = low
                option._close = close
                option.volume = volume
            

    def close(self):
        "Closes the market, preventing buying and selling."
        self.is_open = False

    def save(self):
        "Save the market, and options to the database"
        if not self.id:
            self.marketplace.sql_new_market(self)
            for o in self.stocks:
                o.save()

    def add_option(self, text):
        "Creates a new option. Returns the option."
        if self.is_open:
            raise Exception("Can't add option if market is open")
        stock = _Stock(text, self)
        self.stocks.append(stock)
        for s in self.stocks:
            # If a new option is added, naturally the cost of each one will go down.
            # e.g. 4 options would be $25, but 5 would be $20
            s.cost = self._find_current_price(s)
        if self.marketplace.autosave:
            self.marketplace.sql_add_option(self, stock)
        return stock

    def new_candle(self):
        "Creates a new 'candle', which is the high, low, open and close values of a trading day."
        for option in self.stocks:
            if self.id:
                self.marketplace.sql_close_candle(option)
            option._open = option.cost
            option._high = option.cost
            option._low = option.cost
            if self.id:
                self.marketplace.sql_new_candle(option)
                
    def change_comments(self, comments):
        "Change the comments section of the market."
        self.comments = comments
        self.marketplace._change_comments(self, comments)

    def call(self, stock):
        "Determines which option in a market is true, closing it, and settling money."
        if not self.id: return #TODO: market shouldn't have to be saved
        for player in stock.shares.keys():
            amount = stock.shares[player]["amount"]
            self.marketplace.bank[player] += amount * 100
            self.marketplace._change_player_amount(player, self.marketplace.bank[player])
        self.marketplace._call(self)
        self.close()

    def _find_current_price(self, stock):
        "Finds the current cost of a single share in an item. Returns cost."
        e, b = math.e, self.b
        cost = e**(stock.num_shares/b) / sum([e**(q.num_shares/b) for q in self.stocks]) * 100
        return cost

    def _find_total_cost(self, share, amount):
        "Finds the total cost of multiple shares of an item.  Returns that cost."
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
        "Updates the costs of all the shares in the market."
        for stock in self.stocks:
            stock.cost = self._find_current_price(stock)
            if self.is_open:
                stock.update_candle()
        
    def __str__(self):
        string = self.text
        label = iter("abcdefghijklmnopqrstuvwxyz")
        for s in self.stocks:
            string += "\n{}: {}".format(next(label), s)
        return string

    def __repr__(self):
        return "<Market: {}>".format(self.text)

class Marketplace:
    "A collection of all the markets and categories--the whole economy itself."
    def __init__(self, autosave = False):
        self.autosave = False # temporarily just to add default "misc" and "Admin".
        self.con = sql.connect("karmamarket.sql")
        self.cur = self.con.cursor()
        self.markets = []
        self.categories = []
        #TODO: is this safe? 
        self.bank = {"admin": 0}
        #none_cat = _Category(self, "None", "None", "", 0)
        #none_cat.add_judge("admin")
        #none_cat.add_judge("sje46")
        #self.categories = [none_cat]
        self.id_handler = {}
        self.option_id_handler = {}
        self.autosave = autosave


    def new_market(self, text, author="admin", category=None, close_time=None, rules=None, b=100, comments="", autosave=False):
        """Creates and returns a new prediction market."""
        autosave_market = autosave
        market = _Market(self, text, author, category, close_time, rules, b, comments)
        if not category: 
            # make it the "None" category.
            category = self.categories[0]
        if author not in category.judges:
            raise Exception("Author is not a judge in this category")
        self.markets.append(market)
        if self.autosave and not autosave_market:
            self.sql_new_market(market)
        return market

    def sql_new_candle(self, option):
        "Creates a new entry into the history database at the beginning of a trading day."
        self.cur.execute("""
            INSERT INTO history
                (option_id, date, open, high, low, volume)
            VALUES (?, datetime("now"), ?, ?, ?, 0)
            """, (option.id, option.open, option.high, option.low))
        self.con.commit()

    def sql_update_candle(self, option):
        "Updates the latest entry for the option with trading day stats."
        self.cur.execute("""
            UPDATE history set high = ?, low = ?, volume = ?
            WHERE option_id = ? ORDER BY date DESC LIMIT 1 """, (option.high, option.low, option.volume, option.id))
        self.con.commit()
    def sql_close_candle(self, option):
        "Closes a trading day in the database."
        self.cur.execute("""
            UPDATE history SET close = ?
            WHERE option_id = ? ORDER BY date DESC LIMIT 1""", (option.cost, option.id))
        self.con.commit()
    def sql_get_history(self, option, num_days):
        """Gets the history of an option."""
        self.cur.execute("""
            SELECT option_id, date, open, high, low, close, volume FROM history
            WHERE option_id = ? ORDER BY date LIMIT ?""", (option.id, num_days))
        results = self.cur.fetchall()
        return results
#    def sql_add_history(self, option):
#        "Closes a trading day in the database."
#        #TODO: don't add to the history, just close the last one.
#    #def sql_close_candle(self, option):
#        self.cur.execute("""
#            INSERT INTO history 
#                (option_id, date, open, high, low, close, volume)
#            VALUES
#                (?, date("now"), ?, ?, ?, ?, ?)""", (option.id, option.open, option.high, option.low, option.cost, option.volume))
#        
#        self.con.commit()

    def sql_new_market(self, market):
        "Adds a new market t othe database."
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
        "Creates a new category. Returns that category."
        #TODO: separate SQL stuff from this
        self.cur.execute("""
            INSERT INTO categories
                (short, long, extra)
            VALUES
                (?, ?, ?)""", (short, long_, extra))
        self.cur.execute("""SELECT last_insert_rowid()""")
        self.con.commit()
        result = self.cur.fetchone()[0]
        category_id = result
        category = _Category(self, short, long_, extra, category_id)
        self.categories.append(category)
        return category
        
    def sql_add_judge(self, category_id, judge):
        "Adds a judge to the database."
        #TODO: change name
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


    def sql_add_option(self, market, option):
        """Adds an option for a market to the database. Returns the option ID"""
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
        return result
        
    def _buy_share(self, option, player, amount, cost):
        #TODO: rename
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
                    (player_id, amount, option_id, cost)
                VALUES
                    (?, ?, ?, ?)
                """, (player_id, amount, option_id, cost))
        else:
            self.cur.execute("""
                UPDATE outstanding_shares
                SET amount = amount + ?, cost = cost + ?
                WHERE player_id = ? AND option_id = ?
                """, (amount, cost, player_id, option_id))

        self.con.commit()
    def _call(self, market):
        "Handles database when a market is called."
        #TODO: rename
        self._delete_outstanding(market)
        self.cur.execute("UPDATE markets set closed=1 WHERE market_id=?", (market.id,))
        self.con.commit()

    def _change_player_amount(self, player, amount):
        "Change the amount of money a player has in the database."
        #TODO: rename
        self.cur.execute("""
            SELECT player_id FROM bank WHERE name = ?""", (player,))
        player_id = self.cur.fetchone()[0]
        self.cur.execute("""
            UPDATE bank set money = ?
            WHERE player_id = ?""", (amount, player_id))
        self.con.commit()

    def _delete_outstanding(self, market):
        """Deletes the outstanding shares in the database."""
        #TODO: rename
        for stock in market.stocks:
            self.cur.execute("""
                DELETE FROM outstanding_shares
                WHERE option_id = ?""", (stock.id,))

    def _delete_data(self):
        """Destroys the database."""
        #TODO: rename
        tables = ["bank", "markets", "options", "categories", "judges", "outstanding_shares"]
        for t in tables:
            self.cur.execute("""
                DROP TABLE {}""".format(t))
        self.con.commit()
    def _change_comments(self, market, comments):
        """Updates the comments part of a market."""
        #TODO: rename
        self.cur.execute("""
            UPDATE markets 
            set comments = ?
            WHERE market_id = ?
            """, (comments, market.id))
        self.con.commit()
    def _create_test_data(self):
        """Creates test data in the database."""
        #TODO: rename
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
        #TODO: rename

        # Load categories
        self.cur.execute("""
            SELECT * FROM categories""")
        results = self.cur.fetchall()
        for c in results:
            cat_id, short, long_, extra = c
            category = _Category(self, short, long_, extra, category_id=cat_id)
            self.categories.append(category)

        # Load markets
        self.cur.execute("""
            SELECT * FROM markets""")
        results = self.cur.fetchall()
        for m in results:
            m_id, text, author, rules, category_id, close_time, b, closed,  comments = m
            # By default, make it "None" category
            category = self.categories[0]
            for cat in self.categories:
                if cat.category_id == category_id:
                    category = cat
                    break

            loaded_market = _Market(self, text, author, category, close_time, rules, b, comments)
            self.id_handler[loaded_market] = m_id
            self.markets.append(loaded_market)

            # Load the options from this market
            self.cur.execute("""
                SELECT * FROM options
                WHERE market_id = ?""", (m_id,))
            option_results = self.cur.fetchall()
            for s in option_results:
                option_id, market_id, text = s
                loaded_stock = _Stock(text, loaded_market)
                self.option_id_handler[loaded_stock] = option_id
                loaded_market.stocks.append(loaded_stock)
                
                # Put data about how much each player bought of each share into the options
                self.cur.execute("""
                    SELECT * FROM outstanding_shares
                    WHERE option_id = ?""", (option_id,))
                shares_results = self.cur.fetchall()
                for _, amount, player_id, cost in shares_results:
                    self.cur.execute("SELECT name FROM bank WHERE player_id = ?", (player_id,))
                    player_name = self.cur.fetchone()[0]
                    loaded_stock.num_shares += amount
                    if not player_name in loaded_stock.shares.keys():
                        loaded_stock.shares[player_name] = dict()
                        loaded_stock.shares[player_name]["amount"] = 0
                        loaded_stock.shares[player_name]["cost"] = 0
                    loaded_stock.shares[player_name]["amount"] += amount
                    loaded_stock.shares[player_name]["cost"] += cost
            loaded_market.reopen()
            

                    
        # Get player data 
        self.cur.execute("""
            SELECT * FROM bank""")
        results = self.cur.fetchall()
        for p in results:
            p_id, name, money, in_play = p
            self.bank[name] = money

        # Get judge data
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
                (option_id INTEGER, amount UNSIGNED INTEGER, player_id INTEGER, cost REAL,
                FOREIGN KEY (option_id) REFERENCES options(option_id),
                FOREIGN KEY (player_id) REFERENCES bank(player_id))
                """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS history
                (option_id INTEGER, date REAL, open REAL, high REAL, low REAL, 
                close REAL, volume INTEGER);""")
        try:
            self.create_new_category("MISC", "Miscellaneous")
        except: 
            pass
        self.con.commit()
