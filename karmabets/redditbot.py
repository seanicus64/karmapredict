#!/usr/bin/env python3
import sys 
import requests
import praw
from string import ascii_lowercase
import prawcore
import karmamarket
import datetime
import time
import traceback
import random
import validators
from pprint import pprint
hub_subreddit = "KarmaPredict"
class Redditbot:
    footer = "\n-------\n|💰💰💰|[WTF even is this?](https://www.reddit.com/r/{}/wiki/index/info)|[Your Shares](https://reddit.com/message/compose/?to=KarmaPredictBot&subject=MyShares&message=MyShares!)|[Subreddit](/r/{})|This bot is still in beta; please send [us](https://www.reddit.com/message/compose?to=/r/{}) any issues|💰💰💰\n|:-:|:-:|:-:|:-:|:-:|:-:|".format(hub_subreddit, hub_subreddit, hub_subreddit)
    def create_market_view(self, market, submission=None, wiki=False, viewtype="submission"):
        "Create a reddit message to represent the current market. Returns the formatted text."
        
#        reply_text =  "**ID**: #{} {}  \n".format(market.id, "  \n**Submission**:{}".format(submission.permalink) if submission else "")
        reply_text = "**ID**: #{}  ".format(market.id) if market.id else ""
        reply_text += "**Submission**: {}  \n".format(submission.permalink) if submission else ""
        reply_text += "**Wiki**: /r/{}/wiki/{}/{}  \n".format(hub_subreddit, market.category.short, market.id) if wiki and market.id else ""
        reply_text += "{}**{}**  \n\n".format("**This market is CLOSED!**  \n" if not market.is_open else "", market.text.lstrip())
        reply_text += "Label|Option|Cost AKA Probability|Volume|Cost of 5|Cost of 25| Cost of 100\n"
        reply_text += "  --:|:--   |:--                 |   --:|      --:|       --:|         --:\n"
        label = iter(ascii_lowercase.upper())
        sorted_stocks = sorted(market.stocks, key=lambda s: -1* s.cost)
        for o in sorted_stocks:
            label = ascii_lowercase.upper()[market.stocks.index(o)]
            reply_text += "|**{}**|{}|${:,.2f}|{}|${:,.2f}|${:,.2f}|${:,.2f}|\n".format(label, o.text, o.cost, o.num_shares,
                    market._find_total_cost(o, 5), market._find_total_cost(o, 25), market._find_total_cost(o, 100))
        
        reply_text += "\n**b Value**: {}  \n**Category**: {}  \n".format(market.b, market.category if not hasattr(market.category, "long") else market.category.long)
        #if not submission and not wiki:
        # if this comment IS a submission (submission wont link to itself)
        if viewtype == "submission":
#        if not submission:
            reply_text += "To buy seven shares of option A (reply directly to this):\n\n    buy A 5\n"
            reply_text += "To sell three shares of option B:\n\n    sell B 3\n"
            reply_text += "To buy $200 dollars worth of shares of option C:\n\n    buy $200 C\n\n"
            
            reply_text += "For each correct share, you will get $100  \nFor each wrong share, you get nothing!  \n"
            reply_text += "All redditors get $5000 by default!  \n"
            reply_text += "**Disclaimer**: This is fake money; you can't get free cash that easily!\n"
        # if this is a comment
        elif viewtype == "comment":
            reply_text += "[How to play.](https://i.imgur.com/SatSnjJ.png)  \n" 
        
        #if submission or wiki:
        #    reply_text += self.footer
        #TODO: implement this, but in submission only.  imgur only for comments
        #reply_text += self.footer
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
                market = line.partition(":")[2].lstrip()
            elif first_word == "*" and len(split) > 1:
                options.append(line.partition("* ")[2])
        if category:
            for cat in self.mp.categories:
                print(cat.short)
                if cat.short == category:
                    category = cat
                    break
        else: 
            # Make it "None" category by default
            category = self.mp.categories[0]
        if type(category) is str: 
            raise Exception("Not a valid category")
        if not market:
            raise Exception("No market text given")
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

        market_view = self.create_market_view(new_market, wiki=True, viewtype="confirm")
        message = "Please ensure that the following market is correct. Respond with 'Confirm.'\
        and it will open.  Otherwise, respond with the predictbot_new_market command with the \
        required changes, paying attention to the syntax here: [TODO].  The previous attempt will\
        be garbage collected.\n\n---\n\n{}{}""".format(market_view, self.footer)

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
        message += self.footer

        item.author.message("KarmaPredictBot: Your shares", message)
    def handle_deny(self, item):
        market_rand_id = int(item.subject.split()[4].strip("[]"))
        try:
            market = self.random_ids[market_rand_id]
            assert market
        except: 
            raise Exception("Market not found.")
        if market.is_open: return
        if market.comments: return
        self.mp.markets.remove(market)
        del self.random_ids[market_rand_id]
        return
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
        selftext_message = self.create_market_view(market, wiki=True, viewtype="submission")
        wiki_selftext_message = self.create_market_view(market, wiki=False, viewtype="wiki")
        thread = self.reddit.subreddit(hub_subreddit).submit(title, selftext=selftext_message+self.footer)
        wiki = self.reddit.subreddit(hub_subreddit).wiki.create("{}/{}".format(market.category.short, market.id), wiki_selftext_message)
        self.updanda_dict[market] = dict()
        self.updanda_dict[market]["submission"] = thread
        self.updanda_dict[market]["comments"] = []
        self.change_comments(market)
        self.edit_wiki_category(market.category)
    
    def handle_placement(self, item):

                        #comment = self.reddit.comment(id=s[3:])
        url = item.subject
        author = item.author
        body = item.body.split()
        which_market = None
        url = None
        for word in body[1:]:
            if word.startswith("#") and len(word) > 1 and word[1:].isdigit():
                which_market = int(word[1:])
            if validators.url(word):
                url = word
        if not any((which_market, url)):
            return Exception("Bad placement syntax")

        market = None
        for m in self.mp.markets:
            if m.id == which_market:
                market = m
        if not market:
            raise Exception("Market not valid.")
        comment = self.reddit.comment(url=url)

        if self.check_if_submission_watched(comment, market):
            item.reply("There is already a comment on that thread.")
            return
#    def check_if_submission_watched(self, comment, market):


        market_view = self.create_market_view(market, submission=self.updanda_dict[market]["submission"], viewtype="comment")
        market_view += self.footer
        new_comment = comment.reply(market_view)
        print(len(self.updanda_dict[market]))

        print(self.updanda_dict[market])

        self.add_updandum(new_comment, market)
        print(len(self.updanda_dict[market]))
        print(self.updanda_dict[market])
        pass
    def edit_wiki_category(self, category):
        string =  "**Short**: {}  \n**Long**: {}  \n".format(category.short, category.long)
        string += "**Judges**:  \n"
        for j in category.judges:
            string += "* {}  \n".format(j)
        string += "**Markets**:  \n\n"
        string += "|Market_ID|Market|Volume|\n"
        string += "|--:|:--|:-:|\n"
        for m in reversed(self.mp.markets):
            if m.category == category and m.is_open:
                string += "|{}|[{}]({})|{}|\n".format(m.id, m.text, "http://reddit.com/r/{}/wiki/{}/{}".format(
                    hub_subreddit, category.short, m.id), sum([x.num_shares for x in m.stocks]))
        self.reddit.subreddit(hub_subreddit).wiki[category.short].edit(string)
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
        if not market.is_open:
            raise Exception("Market is closed.")
        try:
            requested_stock = market.stocks[ascii_lowercase.index(option_label)]
        except IndexError:
            raise Exception("Invalid option")
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
                redditor.message("Market #{} has been settled.".format(market.id), message)
            self.change_comments(market, True)
            del self.updanda_dict[market]
    def get_amount_from_money(self, command, money, item, market, requested_stock):
        
        if command == "buy":
            temp_amount = 0
            while True:
                cost = market._find_total_cost(requested_stock, temp_amount)
                # Because we don't want to actually go over the amount we have
                print(type(cost), cost)
                print(type(money), money)
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
            #TODO: what if no "sell"?
            elif word == "all" and command == "sell":
                amount_label = "all"

            elif word.startswith("#"): # finds the id for the market
                market_id = int(word[1:])
        if not option_label: raise Exception("No option specified.")
            
        # we find which market it is...
        if market_id:
            for m in self.mp.markets:
                if m.id == market_id:
                   market = m
        if not market: raise Exception("Market not specified or inferred.")
        if not market.is_open:
            raise Exception("Market is closed")

        requested_stock = market.stocks[ascii_lowercase.index(option_label)]
        name = item.author.name
        if amount_label.startswith("$"):
            amount = int(amount_label[1:])
            if command == "sell":
                amount *= -1
            amount_of_shares = self.get_amount_from_money(command, amount, item, market, requested_stock)
        elif amount_label == "all":
            amount_of_shares = -1 * requested_stock.shares[name]["amount"]
        else:
            amount_of_shares = int(amount_label)
            if command == "sell": amount_of_shares *= -1 
        self.mp.create_new_player(name, 20000)
        before = self.mp.bank[name]
        requested_stock.buy(name, amount_of_shares)
        self.changed_markets.add(market)
        self.message_player_bought_shares(item.author, before, requested_stock, amount_of_shares)
        
        # If this was a comment, potentially make a new comment reply and watch it.
        if type(item) is praw.models.reddit.comment.Comment:
            if not self.check_if_submission_watched(item, market):
                updandum = item.reply(self.create_market_view(market, submission=self.updanda_dict[market]["submission"], viewtype="comment") + self.footer)
                self.add_updandum(updandum, market)
    def get_market_from_submission(self, submission):
        "Gets the market from a submission object. Returns the market."
        for market in self.updanda_dict.keys():
            if submission == market.submission:
                return market
        return None
    def get_history_summary(self, option, days):
        results = self.mp.sql_get_history(option, days)
        string =  "ID|Date|Open|High|Low|Close|Volume\n"
        string += ":-:|:-- | --:| --:|--:|  --:| :-:  \n" 
        for r in results:

            if r[-1] == 0 and len(results) > 1: continue
            try:
                string += "{}|{}|{:,.2f}|{:,.2f}|{:,.2f}|{:,.2f}|{:,}\n".format(r[0], r[1][:10], *r[2:])
            except TypeError:
                string += "{}|{}|{:,.2f}|{:,.2f}|{:,.2f}|{}|{:,}\n".format(r[0], r[1][:10], *r[2:])
            except Exception as err:
                print("ERROR")
                print(err)
        return string
    def parse_item(self, item):
        "Parses every item in queue and acts on them."
        print(item.body)
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
        first_line = list(filter(lambda x: x.lower() not in ("predictbot", hub_subreddit , "karmapredictbot"), first_line))
        command = first_line[0].lower().strip(".,?!")
        # handle all the commands that necessarily take place over PM
        if type(item) is praw.models.reddit.message.Message:
            if command == "confirm":
                self.handle_confirm(item)
                return
            elif command == "deny":
                self.handle_deny(item)
                return
            elif command == "myshares":
                self.handle_myshares(item)
                return
#            elif command == "test":
#                self.edit_wiki_category(self.mp.markets[-1].category)
            elif command == "place":
                
                self.handle_placement(item)
                print("Successfully ran")
        # the only multiline command
        if len(first_line) == 1 and command == "new_market":
            self.handle_new_market(item)
        else:
            for l in item.body.split("\n"):
                line = l.split()
                line = list(filter(lambda x: x.lower() not in ("predictbot", "karmapredict", "karmapredictbot", "/u/karmapredictbot"), line)) 
                if not line: continue
                command = line[0]  
                if command == "call":
                    self.handle_call(item, line, market)
                if command in ("buy", "sell"):
                    print("buying")
                    self.handle_buy(item, line, market) 
    
    def change_comments(self, market, delete=False):
        "Stores the comments and threads to be updated in the comments section of the markets database"
        entry = self.updanda_dict[market]
        if delete:
            market.change_comments("")

        print(self.updanda_dict[market]["submission"])
        submission = self.updanda_dict[market]["submission"]
        string = "{};".format(submission.fullname if submission else "")
#        string = "{};".format(self.updanda_dict[market]["submission"].fullname)
        for u in reversed(self.updanda_dict[market]["comments"]):
            if len(string) + len(u.fullname) > 255:
                break
            string += "{};".format(u.fullname)
        string.rstrip(";")
        market.change_comments(string)

    def check_if_submission_watched(self, comment, market):
        "Checks if the submission a comment is in is being watched, returns bool"
        if comment.submission == self.updanda_dict[market]["submission"]:
            return True
        for u in self.updanda_dict[market]["comments"]:
            if u.submission == comment.submission:
                print(u.submission)
                print("submission is being watched")
                return True
        print("Submission is not being watched")
        return False

    def add_updandum(self, comment, market):
        "Adds a comment which is to be edited when the market changes."
        # dog-latin for "that which is to be updated"
        print("add_updandum method")
        if not self.check_if_submission_watched(comment, market):
            print("="*30)
            print(self.updanda_dict[market]["comments"])
            self.updanda_dict[market]["comments"].append(comment)
            print(self.updanda_dict[market]["comments"])
            print("submission is not being watched")
            print("="*30)
        self.change_comments(market)

    def message_player_bought_shares(self, player, before, share, amount ):
        " Tells the player the shares they bought and how it does or could affect his money."
        name = player.name
        after = self.mp.bank[name]
        market_id = share.market.id
        option = share.text
        amount_before = share.shares[name]["amount"] - amount
        amount_after = share.shares[name]["amount"]
        
        message =  "Current Bank\n===\n"
        message += "|Player|Bank Before|Bank After|Difference|Potential Profit|\n"
        message += "|:--   |        --:|       --:|    :-:   |       :-:      |\n"
        message += "|{}    |${:,.2f}   |${:,.2f}  |  ${:,.2f}|${:,.2f}        |\n\n".format(name, before, after, after-before, amount * 100 + (after-before))
        message += "Your Changed Shares\n===\n"
        message += "|Market ID|Option|Amount|Amount Change|\n"
        message += "|:--      |   --:|   --:|     :-:     |\n"
        message += "|{}       |{}    |{}    |{}{}         |\n\n".format(market_id, option, amount_after, "-" if amount < 0 else "+", amount)

        message += self.footer
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
        #TODO: when pushshift is off, comments are staggered 1 late
        #TODO: direct replies arent inferring which market
        #TODO: able to buy/sell on closed markets
        inbox_stream = self.reddit.inbox.stream(pause_after=-1, skip_existing=True)
        # Ten seconds off to give the pushshift API time to process new comments.
        print("Beginning parsing")
        begin = int(datetime.datetime.now().timestamp()) - 10
        end = 0
        this_period = []
        this_period = set()
        top_fifteen = []
        using_pushshift = True
        using_pushshift = False #TODO: pushshift has been very slow and unreliable!
        next_period = []
        while True:
            next_period = set()
            self.changed_markets = set()
            if using_pushshift:
                time.sleep(10)
                end = int(datetime.datetime.now().timestamp()) - 10
                # Store all comments and messages so they can be processed later.
                try:
                    for comment in self.get_pushshift(begin, end):
                        #this_period.append(comment)
                        this_period.add(comment)
                except: continue
            try:
                for item in inbox_stream:
                    if not item: break
                    print("inbox item: {}, type: {}".format(item, type(item)))
                    #next_period.append(item)
                    next_period.add(item)
            except prawcore.exeptions.ServerError:
                continue
            
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
#            if begin_time.day != end_time.day:
            if begin_time.day != end_time.day:
                print("New day: {}".format(end_time.day))
                for m in self.mp.markets:
                    print("New candle for {}".format(m.id))
                    m.new_candle()
                pass

            ranked = sorted(self.mp.bank.items(), key=lambda x: x[1])
            ranked.reverse()
            next_top_fifteen = ranked[:15]
            #if begin_time.hour != end_time.hour and next_top_fifteen != top_fifteen:
            if begin_time.second != end_time.second and next_top_fifteen != top_fifteen:
                self.update_scoreboard()
            top_fifteen = next_top_fifteen
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
        text += "\nLast edited {}".format(datetime.datetime.utcnow().strftime("%b/%d %H:%M:%S UTC"))
        wikipage = self.reddit.subreddit(hub_subreddit).wiki["config/sidebar"]
        wikipage.edit(text)
        widgets = self.reddit.subreddit(hub_subreddit).widgets
        for w in widgets.sidebar:
            w.progressive_images = True
            if w.shortName == "Scoreboard":
                w.mod.update(text=text)
                return

    def update_views(self, market):
        # When a market updates, edit the main thread and comments that show this market
        if not market in self.updanda_dict:
            return
        comments = self.updanda_dict[market]["comments"]
        submission = self.updanda_dict[market]["submission"]
        market_view = self.create_market_view(market, wiki=True, viewtype="submission")
        changed = False
        title = "Market: {}".format(market.text)
        is_valid_submission = True
        try:
            x = submission.title
        except:
            is_valid_submission = False
        if is_valid_submission:
            if any((submission.archived, submission.locked, submission.removed)):
                submission = self.reddit.subreddit(hub_subreddit).submit(title, selftext=market_view+self.footer)    
                self.updanda_dict[market]["submission"] = submission
                changed = True
            try: submission.edit(market_view)
            except Exception as e:
                pass
                print(e)
        
        market_view = self.create_market_view(market, submission, viewtype="comment") + self.footer
        for c in comments:
            try:
                if any((c.archived, c.locked, c.removed)):
                    self.updanda_dict[market]["comments"].remove(comment)
                    changed = True
                    continue
            except: pass
            try:
                c.edit(market_view)
            except Exception as err:
                print(err)
        if changed:
            self.change_comments(market)
        try:
            self.change_wiki(market)
        except Exception as err:
            print(err)
    def change_wiki(self, market):
        name ="{}/{}".format(market.category.short, market.id)
        wikipage = self.reddit.subreddit(hub_subreddit).wiki[name]
        text = self.create_market_view(market, viewtype="wiki")
        for o in market.stocks: #TODO: FIX!!
            text += "\n\n"+ o.text + "\n\n"
            text += self.get_history_summary(o, 30)
        
        wikipage.edit(text)
    def __init__(self):
        self.mp = karmamarket.Marketplace()
        print("Loading database")
        self.mp._load()
        for market in self.mp.markets:
            first_line = "{}: {}".format(market.id, market.text)
            second_line = "\t{}, {}, Category: {}".format(market.author, "Open" if market.is_open else "Closed", market.category.long)
            print(first_line)
            print(second_line)
        self.text_ids = {}
        self.reddit = praw.Reddit("bot1")

        self.random_ids = {}
        while True:
            print("loading updanda - this may take a while")
            try: 
                self.load_updanda()
                break
            except Exception as e: 
                print(e)
                return
                continue
            
        self.read_everything()
    def load_updanda(self):
        self.updanda_dict = {}
        for wikipage in self.reddit.subreddit(hub_subreddit).wiki:
            _ = wikipage.revision_date
    
        print("LOAD UPDANDA FUNCTION")
        print(len(self.mp.markets))
        print(self.mp.markets)
        for e, m in enumerate(self.mp.markets):
            print(e, "Loading updanda for {}:{}".format(m.id, m.text))
            self.updanda_dict[m] = {"submission": None, "comments": []}#, "wiki": None}
            print("added to updanda_dict")
            split = m.comments.split(";")
            for s in split:
                print("\n{}".format(s))
                if s.startswith("t3"): # is a submission
                    submission = self.reddit.submission(id=s[3:])
                    #retrieving data  turns it into a non-lazy instance, getting a LOT more variables
                    print(submission.fullname, submission.url)    
                    try:
                        _ = submission.title
                    except: 
                        pass
                    
                    self.updanda_dict[m]["submission"] = submission
                elif s.startswith("t1"): # is a comment
                    try:
                        comment = self.reddit.comment(id=s[3:])
                        print(comment.fullname)
                    except:
                        continue
                    self.updanda_dict[m]["comments"].append(comment)
        for market in self.mp.markets:
            print("Loading updanda for {}:{}".format(market.id, market.text))
            sub = self.updanda_dict[market]["submission"]
            try:
                __ = sub.title
            except:
                #TODO
                # Need to create a new submission or just update the wiki if no submission is available
                self.updanda_dict[market]["submission"] = None


def main():
    mp = karmamarket.Marketplace(autosave=True)
    mp._load()
    read_everything(mp)
if __name__ == "__main__":
    try:
        hub_subreddit = sys.argv[1]
    except: pass
    bot = Redditbot()
