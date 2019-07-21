#!/usr/bin/env python3
import requests
import praw
from string import ascii_lowercase
import prawcore
import karmamarket
import datetime
import time
import traceback
import random
class Redditbot:
    def create_market_view(self, market):
        "Create a reddit message to represent the current market. Returns the formatted text."
        reply_text =  "**ID**: #{}\n".format(market.id)
        reply_text += "{}\n{}\n===\n".format("This market is CLOSED!" if not market.is_open else "", market.text)
        reply_text += "Label|Option|Cost|Volume|Cost of 5|Cost of 25| Cost of 100\n"
        reply_text += "  --:|:--   | --:|   --:|      --:|       --:|         --:\n"
        label = iter(ascii_lowercase.upper())
        for o in market.stocks:
            reply_text += "|**{}**|{}|{:.2f}|{}|{:.2f}|{:.2f}|{:.2f}|\n".format(next(label), o.text, o.cost, o.num_shares,
                    market._find_total_cost(o, 5), market._find_total_cost(o, 25), market._find_total_cost(o, 100))
        
        reply_text += "**b Value**: {}  \n**Category**: {}  \n".format(market.b, market.category if not hasattr(market.category, "long") else market.category.long)
        return reply_text

    def create_new_market(self, comment, autosave=False):
        "Prases a comment to make a market.  Returns that market."
        name = comment.author.name
        market, category, closes, rules = "", "", "", ""
        options = []
        for line in comment.body.split("\n"):
            split = line.split()
            if not split:
                continue
            first_word = split[0].lower()
            if first_word == "category:":
                category = split[1]
            elif first_word == "closes:":
                closes = split[1]
            elif first_word == "rules:":
                rules = line.partition(":")[2]
            elif first_word == "market:":
                market = line.partition(":")[2]
            elif first_word == "*" and len(split) > 1:
                options.append(line.partition("* ")[2])
        if category:
            for cat in self.mp.categories:
                if cat.short == category:
                    category = cat
                    break
        else: 
            # Make it "None" category by default
            category = self.mp.categories[0]

        new_market = self.mp.new_market(text=market, author=name, category=category, close_time=None, rules=rules, autosave=False)
        for o in options:
            new_market.add_option(o)
        return new_market
    def handle_new_market(self, item):
        "Handles the command creating a new market"
        try:
            new_market = self.create_new_market(item, autosave=False)
        except Exception as e:
            raise Exception("Syntax is wrong: {}".format(e))

        market_view = self.create_market_view(new_market)
        message = "Please ensure that the following market is correct. Respond with 'Confirm.'\
        and it will open.  Otherwise, respond with the predictbot_new_market command with the \
        required changes, paying attention to the syntax here: [TODO].  The previous attempt will\
        be garbage collected.\n\n---\n\n{}""".format(market_view)

        # TODO: a silly hack to make sure that not too many markets are awaiting confirmation.
        if len(self.random_ids) > 100:
            self.random_ids = {}
        
        if len(self.random_ids) >= 9000:
            raise Exception("Too many markets are awaiting confirmation")
        while True:
            x = random.randrange(10000)
            if x not in self.random_ids.keys():
                self.random_ids[x] = new_market
                break
        item.author.message("Confirm market creation: [{}]".format(x), message)
    
    def handle_myshares(self, item):
        "Handles the command asking for a summary of a player's shares."
        all_shares = []
        num_shares = 0
        name = item.author.name
        for m in self.mp.markets:
            for option in m.stocks:
                if name in option.shares:
                    if option.shares[name]["amount"] > 0:
                        all_shares.append(option)
                        num_shares += option.shares[name]["amount"]
        message =  "|Player|Bank|# of Shares|# of Options|\n"
        message += "|:--   |:-: |     :-:   |   :-:      |\n"
        message += "|{}    |${:,.2f}|{:,}   |{:,}        |\n\n".format(name, self.mp.bank[name], num_shares, len(all_shares))
        message += "|Market ID|Amount|Money Invested|Option|Market|\n"
        message += "|      --:|   --:|           --:|   --:|:--   |\n"""

        for option in all_shares:
            message += "|{}|{:,}|${:,.2f}|{}|{}|\n".format(option.market.id, option.shares[name]["amount"], option.shares[name]["cost"], option.text, option.market.text)
        message += "\n-------\n|[Info](https://www.reddit.com/r/KarmaPredict/wiki/info)|[Your Shares](https://reddit.com/message/compose/?to=KarmaPredictBot&subject=MyShares&message=MyShares!)|[Subreddit](/r/KarmaPredict)|\n|:-:|:-:|:-:|"

        item.author.message("KarmaPredictBot: Your shares", message)
    def handle_confirm(self, item):
        "Handles confirming a market, which will then open it."
        market_rand_id = int(item.subject.split()[4].strip("[]"))
        try:
            market = self.random_ids[market_rand_id]
            assert market
        except: raise Exception("Market not found.")
        if market.is_open: return
        if market.comments: return
        market.save()
        market.open()
        title = "Market: {}".format(market.text)
        selftext_message = self.create_market_view(market)
        thread = self.reddit.subreddit("KarmaPredict").submit(title, selftext=selftext_message)
        self.updanda_dict[market] = dict()
        self.updanda_dict[market]["submission"] = thread
        self.updanda_dict[market]["comments"] = []
        self.change_comments(market)
    def handle_call(self, item, first_line, market=None):
        "Handles a judge calling a market."
        option_label, market_id = "", ""
        for word in first_line[1:]:
            word = word.lower()
            if len(word) == 1 and word in ascii_lowercase: # determines the label
                option_label = word
            elif word.startswith("#") and len(word) > 1 and word[1:].isdigit():
                market_id = int(word[1:])   # determines the market id

        if not option_label: raise Exception("Option not specified")
        for m in self.mp.markets:
            if m.id == market_id:
                market = m
        if not market:
            raise Exception("Market not specified or inferred.")
        requested_stock = market.stocks[ascii_lowercase.index(option_label)]
        if item.author.name in market.category.judges:
            market.call(requested_stock)
            self.changed_markets.add(market)

            # Just finding all the players who bought into this market
            players = {}
            for option in market.stocks:
                for name in option.shares.keys():
                    num_stocks = option.shares[name]["amount"]
                    if name not in players.keys():
                        players[name] = []
                    if num_stocks > 0:
                        players[name].append(option)


            # Send each player a message about their wins/loses in this market
            have_won = False
            for player, options in players.items():
                message =  "|Market ID|Option|Amount|Win/Lost|\n"
                message += "|:--      |:--   | :-:  |  :-:   |\n"
                for o in options:
                    if not name in o.shares: continue
                    message += "|{}|{}|{}|{}|\n".format(o.market.id, o.text, o.shares[name]["amount"], 
                            "Win" if o is requested_stock else "Lose")
                message += "\n\n"
                after = self.mp.bank[name]
                before = self.mp.bank[name]-requested_stock.shares[name]["amount"]*100
                difference = requested_stock.shares[name]["amount"]
                bank_table =  "|Player|Bank Before|Bank After|Difference|\n"
                bank_table += "|:--   |        --:|       --:|    :-:   |\n"
                bank_table += "|{}    |{:.2f}     |{:.2f}    |{:.2f}    |\n\n".format(name, before, after, difference)
                message += bank_table
                redditor = self.reddit.redditor(name)
                redditor.message("test", message)
    def get_amount_from_money(self, command, money, item):
        
        if command == "buy":
            temp_amount = 0
            while True:
                cost = market._find_total_cost(requested_stock, temp_amount)
                # Because we don't want to actually go over the amount we have
                if cost >= money: 
                    temp_amount -= 1
                    break
                temp_amount += 1
            amount_of_shares = temp_amount

        # Similar to buy, except backwards
        elif command == "sell":
            if item.author.name not in requested_stock.shares.keys():
                raise Exception("User has no shares of this option")
            temp_amount = 0
            
            while True:
                cost = market._find_total_cost(requested_stock, temp_amount)
                if cost <= money or abs(temp_amount) > requested_stock.shares[item.author.name]["amount"]:
                    temp_amount += 1
                    break
                temp_amount -= 1
            amount_of_shares = temp_amount
        return amount_of_shares
    def handle_buy(self, item, first_line, market=None):
        "Handles a player buying a share in a market."
        option_label, amount_label, market_id = "", "1", ""
        command = first_line[0].lower().strip(".!,?")

        # Quickly parse through the arguments given.
        for word in first_line[1:]:
            word = word.lower()
            if len(word) == 1 and word.lower() in ascii_lowercase: # finds the chosen option
                option_label = word.lower()
            elif (word.startswith("$") and word[1:].isdigit()) or word.isdigit(): # finds the amount to buy
                amount_label = word

            elif word.startswith("#"): # finds the id for the market
                market_id = int(word[1:])
        if not option_label: raise Exception("No option specified.")
        #if not amount_label: raise Exception("No amount specified.") #TODO: default amount is 1

        # we find which market it is...
        if market_id:
            for m in self.mp.markets:
                if m.id == market_id:
                   market = m
        if not market: raise Exception("Market not specified or inferred.")

        requested_stock = market.stocks[ascii_lowercase.index(option_label)]
        if amount_label.startswith("$"):
            amount_of_shares = self.get_amount_from_money(command, int(amount_label[1:]), item)
        else:
            amount_of_shares = int(amount_label)

        name = item.author.name
        self.mp.create_new_player(name, 500)
        before = self.mp.bank[name]
        requested_stock.buy(name, amount_of_shares)
        self.changed_markets.add(market)
        self.message_player_bought_shares(item.author, before, requested_stock, amount_of_shares)
        
        # If this was a comment, potentially make a new comment reply and watch it.
        if type(item) is praw.models.reddit.comment.Comment:
            if not self.check_if_submission_watched(item, market):
                updandum = item.reply(self.create_market_view(market))
                self.add_updandum(updandum, market)
    def get_market_from_submission(self, submission):
        "Gets the market from a submission object. Returns the market."
        for market in self.updanda_dict.keys():
            if submission == market.submission:
                return market
        return None
    def parse_item(self, item):
        "Parses every item in queue and acts on them."
        first_line = item.body.split("\n")[0]
        first_line = first_line.split()
        
        market = None
        if type(item) is praw.models.reddit.comment.Comment:
            parent = item.parent()
            market = None
            if type(parent) == praw.models.reddit.submission.Submission:
                for m in self.updanda_dict.keys():
                    if self.updanda_dict[m]["submission"] == parent:
                        market = m
                        break
            elif type(parent) == praw.models.reddit.comment.Comment:
                for m in self.updanda_dict.keys():
                    for comment in self.updanda_dict[m]["comments"]:
                        if comment == parent:
                            market = m
                            break

        # invocation of the bot isn't necessary through PM
        first_line = list(filter(lambda x: x.lower() not in ("predictbot", "karmapredict", "karmapredictbot"), first_line))
        command = first_line[0].lower().strip(".,?!")
        if len(first_line) == 1 and command == "new_market":
            self.handle_new_market(item)
            pass
        elif type(item) is praw.models.reddit.message.Message and command == "myshares":
            self.handle_myshares(item)

        # All items that are direct messages
        if type(item) is praw.models.reddit.message.Message:
            if command == "confirm":
                self.handle_confirm(item)
            elif command == "deny":
                pass
        if command == "call":
            self.handle_call(item, first_line, market)
        if command in ("buy", "sell"):
            self.handle_buy(item, first_line, market) 
    
    def change_comments(self, market):
        "Stores the comments and threads to be updated in the comments section of the markets database"
        string = "{};".format(self.updanda_dict[market]["submission"].fullname)
        for u in self.updanda_dict[market]["comments"]:
            string += "{};".format(u.fullname)
        string.rstrip(";")
        market.change_comments(string)

    def check_if_submission_watched(self, comment, market):
        "Checks if the submission a comment is in is being watched, returns bool"
        #TODO: the subm as well
        for u in self.updanda_dict[market]["comments"]:
            if u.submission == comment.submission:
                return True
        return False

    def add_updandum(self, comment, market):
        "Adds a comment which is to be edited when the market changes."
        # dog-latin for "that which is to be updated"
        if not self.check_if_submission_watched(comment, market):
            self.updanda_dict[market]["comments"].append(comment)
        self.change_comments(market)

    def message_player_bought_shares(self, player, before, share, amount ):
        " Tells the player the shares they bought and how it does or could affect his money."
        name = player.name
        after = self.mp.bank[name]
        market_id = share.market.id
        option = share.text
        amount_before = share.shares[name]["amount"] - amount
        amount_after = share.shares[name]["amount"]

        message =  "|Player|Bank Before|Bank After|Difference|Potential Profit|\n"
        message += "|:--   |        --:|       --:|    :-:   |       :-:      |\n"
        message += "|{}    |{:.2f}     |{:.2f}    |{:.2f}    |{:.2f}          |\n\n".format(name, before, after, after-before, amount * 100)
        message += "|Market ID|Option|Amount|Amount Change|\n"
        message += "|:--      |   --:|   --:|     :-:     |\n"
        message += "|{}       |{}    |{}    |{}           |\n\n".format(market_id, option, amount_after, amount)

        message += "\n-------\n|[Info](https://www.reddit.com/r/KarmaPredict/wiki/info)|[Your Shares](https://reddit.com/message/compose/?to=KarmaPredictBot&subject=MyShares&message=MyShares!)|[Subreddit](/r/KarmaPredict)|\n|:-:|:-:|:-:|"
        player.message("Predictbot: You bought shares", message)

    def get_pushshift(self, begin, end):
        "Gets all references to the bot, and turns them into comments for processing."
        built_call = "https://api.pushshift.io/reddit/comment/search/?q=predictbot&limit=100&after={}&before={}".format(begin, end)
        print(built_call)
        #built_call = "https://api.pushshift.io/reddit/comment/search/?q=the&limit=100&after={}&before={}".format(begin, end)
        request = requests.get(built_call, headers={"User-Agent": "PredictBot"})
        json = request.json() #TODO: json decode error
        comments = json["data"]
        print(len(comments))
        for rawcomment in comments:
            comment = praw.models.Comment(self.reddit, _data = rawcomment)
            yield comment

    def read_everything(self):
        "The main loop.  Reads mentions, privage messages, and acts on them."
        inbox_stream = self.reddit.inbox.stream(pause_after=-1, skip_existing=True)
        # Ten seconds off to give the pushshift API time to process new comments.
        begin = int(datetime.datetime.now().timestamp()) - 10
        this_period = []
        while True:
            next_period = []
            self.changed_markets = set()
            #items = []
            time.sleep(10)
            end = int(datetime.datetime.now().timestamp()) - 10
            # Store all comments and messages so they can be processed later.
            for comment in self.get_pushshift(begin, end):
                #items.append(comment)
                this_period.append(comment)
            for item in inbox_stream:
                if not item: break
                #if type(item) is praw.models.reddit.message.Message:
                    #items.append(item)
                print("inbox item: {}, type: {}".format(item, type(item)))
                next_period.append(item)
            
            # sort all comments and messages by the time they were created to prevent time manipulation
            sorted_period = sorted(this_period, key=lambda x: x.created_utc)
            for item in sorted_period:
                try:
                    self.parse_item(item)
                except:
                    print(traceback.format_exc())
            
            # For all the markets that changed in this period, update all of their active views.
            for market in self.changed_markets:
                self.update_views(market)


            this_period = next_period
            end_time = datetime.datetime.fromtimestamp(end)
            begin_time = datetime.datetime.fromtimestamp(begin)
            if begin_time != end_time:
                #TODO: add history support
                for m in self.mp.markets:
                    m.new_candle()
                pass
            self.update_scoreboard()
            begin=end
             
    def update_scoreboard(self):
        "Creates a ranking of the richest players."
        ranked = sorted(self.mp.bank.items(), key=lambda x: x[1])
        ranked.reverse()
        text =  "Scoreboard\n=====\n"
        text += "Rank|Name|Amount\n"
        text += "--:| --:|--:\n"
        for e, (player, amount) in enumerate(ranked[:15], 1):
            text += "{}.|{}|${:,.2f}\n".format(e, player, amount)

    def update_views(self, market):
        # When a market updates, edit the main thread and comments that show this market
        comments = self.updanda_dict[market]["comments"]
        submission = self.updanda_dict[market]["submission"]
        for u in comments + [submission]:
            #TODO: handle deletions, bans, archival after 6 months, etc
            market_view = self.create_market_view(market)
            try:
                u.edit(market_view)
            except Exception as err:
                print(err)
    def __init__(self):
        self.mp = karmamarket.Marketplace()
        self.mp._load()
        #TODO: text_ids like USPOL.32
        self.text_ids = {}
        self.reddit = praw.Reddit("bot1")

        self.updanda_dict = {}
        self.random_ids = {}
        # get all the updanda to be updated from database
        for m in self.mp.markets:
            self.updanda_dict[m] = {"submission": None, "comments": []}
            split = m.comments.split(";")
            for s in split:
                if s.startswith("t3"): # is a submission
                    submission = self.reddit.submission(id=s[3:])
                    self.updanda_dict[m]["submission"] = submission
                elif s.startswith("t1"): # is a comment
                    try:
                        comment = self.reddit.comment(id=s[3:])
                    except:
                        continue
                    self.updanda_dict[m]["comments"].append(comment)
        self.read_everything()
def main():
    mp = karmamarket.Marketplace()
    mp._load()
    read_everything(mp)
if __name__ == "__main__":
    bot = Redditbot()
