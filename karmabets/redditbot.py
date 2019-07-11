#!/usr/bin/env python3
import requests
import praw
from string import ascii_lowercase
import prawcore
import karmamarket
import datetime
import time
import traceback
class Redditbot:
    def create_market_view(self, market):
        
        reply_text = """
**ID**: #{}   
{}  
{}  
====

|Label|Option|Cost|Volume|Cost of 5|Cost of 25|Cost of 100|
|  --:|:--   | --:|   --:|      --:|       --:|        --:|
""".format(market.id, "This market is CLOSED!" if not market.is_open else "",
            market.text)
        label = iter(ascii_lowercase.upper())
        for o in market.stocks:
            reply_text += "|**{}**|{}|{:.2f}|{}|{:.2f}|{:.2f}|{:.2f}\n".format(next(label), o.text, o.cost, o.num_shares, market._find_total_cost(o, 5), market._find_total_cost(o, 25), market._find_total_cost(o, 100))
        reply_text += "**b Value**: {}  \n**Category**: {}  \n".format(market.b, market.category if not hasattr(market.category, "long") else market.category.long)
        return reply_text
    def create_new_market(self, comment):
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
                options.append(line.partition("*")[2])

        new_market = self.mp.new_market(text=market, author=name, category=category, close_time=None, rules=rules)
        for o in options:
            new_market.add_option(o)
        return new_market

    def parse_item(self, item):
        first_line = item.body.split("\n")[0]
        first_line = first_line.split()

        # Creating a new prediction market.
        if len(first_line) == 2 and first_line[1] == "new_market":
            try:
                new_market = self.create_new_market(item)
            except Exception as e: 
                raise Exception("Syntax is wrong: {}".format(e))
            market_view = self.create_market_view(new_market)
            message = "Please ensure that the following market is correct. Respond with 'Confirm.'\
            and it will open.  Otherwise, respond with the predictbot_new_market command with the \
            required changes, paying attention to the syntax here: [TODO].  The previous attempt will\
            be garbage collected.\n\n---\n\n{}""".format(market_view)
            item.author.message("Confirm market creation: [{}]".format(new_market.id), message)

        if type(item) is praw.models.reddit.message.Message:# and first_line.split()[0].lower() == "confirm":
            if item.body.lower().strip(".!?") == "myshares":
                all_shares = []
                num_shares = 0
                name = item.author.name
                for m in self.mp.markets:
                    for option in m.stocks:
                        if name in option.shares:
                            if option.shares[name] > 0:
                                all_shares.append(option)
                                num_shares += option.shares[name]
                message = """
|Player|Bank|# of Shares|# of Options|
|:--   |:-: |     :-:   |   :-:      |
|{}    |{:.2f}|{}         |{}          |


|Market ID|Market|Option|Amount|
|      --:|:--   |   --:| :-:  |\n""".format(name, self.mp.bank[name], num_shares, len(all_shares))

                for option in all_shares:
                    message += "|{}|{}|{}|{}|\n".format(option.market.id, option.market.text, option.text, option.shares[name])
                message += "\n-------\n|[Info](https://www.reddit.com/r/KarmaPredict/wiki/info)|[Your Shares](https://reddit.com/message/compose/?to=KarmaPredictBot&subject=MyShares&message=MyShares!)|[Subreddit](/r/LarmaPredict)|\n|:-:|:-:|:-:|"

                item.author.message("KarmaPredictBot: Your shares", message)
            
                            
            if item.body.lower().strip(".!?") in ("confirm", "deny"):
                    

                market_id = int(item.subject.split()[4].strip("[]"))
                market = None
                for m in self.mp.markets:
                    if m.id == market_id:
                        market = m
                        break
                if not market: return
                if market.is_open: return
                if market.comments: return
            if item.body.lower().strip(".!?") == "confirm":
                market.open()
                title = "New Market: {}".format(market.text)
                selftext_message = self.create_market_view(market)
                thread = self.reddit.subreddit("KarmaPredict").submit(title, selftext=selftext_message)
#                market.change_comments(thread.fullname)
                self.updanda_dict[market] = dict()
                self.updanda_dict[market]["submission"] = thread
                self.updanda_dict[market]["comments"] = []
                self.change_comments(market)
            if item.body.lower().strip(".?!") == "deny":
                #TODO: actually delete the created market
                market_id = int(item.subject.split()[4].strip("[]"))
                print("DENIED")
        if len(first_line) == 4 and first_line[1].lower() == "call":
            print("a")
            option_label, market_id = "", ""
            for word in first_line[1:]:
                word = word.lower()
                if word == "predictbot": continue
                if len(word) == 1 and word in ascii_lowercase:
                    option_label = word
                elif word.startswith("#") and len(word) > 1 and word[1:].isdigit():
                    market_id = int(word[1:])
            if not all((option_label, market_id)): raise Exception("bad syntax")
            print("b")
            for m in self.mp.markets:
                #TODO: this entire section
                if m.id == market_id:
                    print("C")
                    market = m
                    requested_stock = m.stocks[ascii_lowercase.index(option_label)]
                    if item.author.name in m.category.judges:
                        print("redditbot: calling {}".format(requested_stock.text))
                        m.call(requested_stock)
                        #market_view = self.create_market_view(m)
                        self.changed_markets.add(m)
                        players = {}
                        print("D")
                        for option in m.stocks:
                            for name, num_stocks in option.shares.items():
                                
                                if name not in players.keys():
                                    players[name] = []
                                if num_stocks > 0:
                                    players[name].append(option)
                        print("E")
                        have_won = False
                        for player, options in players.items():
                            print("PLAYER", player)
                            message =  "|Market ID|Option|Amount|Win/Lost|\n"
                            message += "|:--      |:--   | :-:  |  :-:   |\n"
                            for o in options:
                                if not name in o.shares: continue
                                message += "|{}|{}|{}|{}|\n".format(o.market.id, o.text, o.shares[name], 
                                        "Win" if o is requested_stock else "Lose")
#                                if o is requested_stock:
#                                    table += "|{}|{}|{}|Win|\n".format(option.market.id, option.text, option.shares[name])
#                                else:
#                                    table += "|{}|{}|{}|Lose|\n".format(option.market.id, option.text, option.shares[name])
                            message += "\n\n"
                            after = self.mp.bank[name]
                            before = self.mp.bank[name]-requested_stock.shares[name]*100
                            difference = requested_stock.shares[name]
                            bank_table =  "|Player|Bank Before|Bank After|Difference|\n"
                            bank_table += "|:--   |        --:|       --:|    :-:   |\n"
                            bank_table += "|{}    |{:.2f}     |{:.2f}    |{:.2f}    |\n\n".format(name, before, after, difference)
                            message += bank_table
                            redditor = self.reddit.redditor(name)
                            print(name)
                            print(message)
                            
                            redditor.message("test", message)



                        #split_comments = m.comments.split(";")
                        #for s in split_comments:
                        #    if s.startswith("t="):
                        #
                        #        thread_id = s.partition("t=")[2][3:]
                        #        thread = self.reddit.submission(id=thread_id)
                        #        print("========")
                        #        print(thread)
                        #        thread.edit(market_view)

        if len(first_line) == 5 and first_line[1].lower() in  ("buy", "sell"):
            
            option_label, amount_label, market_id = "", "", ""
            for word in first_line[1:]:
                word = word.lower()
                if word == "predictbot": continue
                if len(word) == 1 and word.lower() in ascii_lowercase:
                    option_label = word.lower()
                #TODO: word ends with %, buy up to that percent.  predictbot buy #3 C 50%
                elif (word.startswith("$") and word[1:].isdigit()) or word.isdigit():
                    amount_label = word

                elif word.startswith("#"):
                    market_id = int(word[1:])
            if not all((option_label, amount_label, market_id)):
                raise Exception("Bad syntax")
            for m in self.mp.markets:
                if m.id == market_id:
                    market = m
                    requested_stock = m.stocks[ascii_lowercase.index(option_label)]
                    if amount_label.startswith("$"): # they want to buy x dollars in stocks
                        amount = int(amount_label[1:]) 
                        if first_line[1] == "buy":
                            temp_amount = 0
                            while True:
                                cost = m._find_total_cost(requested_stock, temp_amount)
                                if cost >= amount: 
                                    temp_amount -= 1
                                    break
                                temp_amount += 1
                            amount_of_shares = temp_amount
                        elif first_line[1] == "sell":
                            if item.author.name not in requested_stock.shares.keys():
                                raise Exception("User has no shares of this option")
                            temp_amount = 0
                            
                            while True:
                                cost = m._find_total_cost(requested_stock, temp_amount)
                                if cost <= - amount or abs(temp_amount) > requested_stock.shares[item.author.name]:
                                    temp_amount += 1
                                    break
                                temp_amount -= 1
                            amount_of_shares = temp_amount
                    else:
                        amount_of_shares = int(amount_label)
                        if first_line[1] == "sell":
                            amount_of_shares *= -1
                    name = item.author.name
                    self.mp.create_new_player(name, 500)
                    before = self.mp.bank[name]
                    requested_stock.buy(name, amount_of_shares)
                    self.changed_markets.add(m)
                    self.message_player_bought_shares(item.author, before, requested_stock, amount_of_shares)
                    
                    if type(item) is praw.models.reddit.comment.Comment:
                        #current_thread = item.submission.fullname
                        # check if thread is being watched
                        # if it's not, create reply
                        #then add reply as updandum
                        if not self.check_if_submission_watched(item, market):

                            updandum = item.reply(self.create_market_view(market))
                            print(self.updanda_dict[m])
                            self.add_updandum(updandum, m)
                            print(self.updanda_dict[m])
    def change_comments(self, market):
        string = "{};".format(self.updanda_dict[market]["submission"].fullname)
        
        for u in self.updanda_dict[market]["comments"]:
            string += "{};".format(u.fullname)
        string.rstrip(";")

        market.change_comments(string)
    def check_if_submission_watched(self, comment, market):
        #TODO: the subm as well
        for u in self.updanda_dict[market]["comments"]:
            if u.submission == comment.submission:
                return True
        return False
    def add_updandum(self, comment, market):
        #dog-latin for "that which is to be updated"
 #       should_add = True
 #       for u in self.updanda_dict[market]["comments"]:
 #           # To prevent spam, only have one comment per submission.
 #           if u.submission == comment.submission:
 #               should_add = False
        if not self.check_if_submission_watched(comment, market):
#        if should_add:
            self.updanda_dict[market]["comments"].append(comment)
        self.change_comments(market)

#        for u in updanda:
#            if reddit.
#        for 
    def message_player_bought_shares(self, player, before, share, amount ):
        name = player.name
        after = self.mp.bank[name]
        market_id = share.market.id
        option = share.text
        amount_before = share.shares[name] - amount
        amount_after = share.shares[name]

        message =  "|Player|Bank Before|Bank After|Difference|Potential Profit|\n"
        message += "|:--   |        --:|       --:|    :-:   |       :-:      |\n"
        message += "|{}    |{:.2f}     |{:.2f}    |{:.2f}    |{:.2f}          |\n\n".format(name, before, after, after-before, amount * 100)
        message += "|Market ID|Option|Amount|Amount Change|\n"
        message += "|:--      |   --:|   --:|     :-:     |\n"
        message += "|{}       |{}    |{}    |{}           |\n\n".format(market_id, option, amount_after, amount)

        message += "\n-------\n|[Info](https://www.reddit.com/r/KarmaPredict/wiki/info)|[Your Shares](https://reddit.com/message/compose/?to=KarmaPredictBot&subject=MyShares&message=MyShares!)|[Subreddit](/r/KarmaPredict)|\n|:-:|:-:|:-:|"
        player.message("Predictbot: You bought shares", message)
    def get_pushshift(self, begin, end):
        built_call = "https://api.pushshift.io/reddit/comment/search/?q=predictbot&limit=100&after={}&before={}".format(begin, end)
        request = requests.get(built_call, headers={"User-Agent": "PredictBot"})
        print(built_call)
        json = request.json()
        comments = json["data"]
        print(len(comments))
        for rawcomment in comments:
            comment = praw.models.Comment(self.reddit, _data = rawcomment)
            yield comment
    def read_everything(self):
        import time
        inbox_stream = self.reddit.inbox.stream(pause_after=-1, skip_existing=True)
        begin = int(datetime.datetime.now().timestamp()) - 10

        while True:
            self.changed_markets = set()
            #TODO: change the markets after all the items are processed
            items = []
            print(begin)
            time.sleep(10)
            end = int(datetime.datetime.now().timestamp()) - 10
            for comment in self.get_pushshift(begin, end):
                print("Item {} came from comments".format(comment.fullname))
                items.append(comment)
            for item in inbox_stream:
                
                if not item: break
                if type(item) is praw.models.reddit.message.Message:
                    print("Item {} came from inbox".format(item.fullname))
                    items.append(item)
            for item in items:
                try:
                    self.parse_item(item)
                except:
                    print(traceback.format_exc())

            for market in self.changed_markets:
                self.update_views(market)

            begin=end
    def update_views(self, market):
        comments = self.updanda_dict[market]["comments"]
        submission = self.updanda_dict[market]["submission"]
        for u in comments + [submission]:
            #TODO: handle deletions, bans, archival after 6 months, etc
            market_view = self.create_market_view(market)
            try:
                u.edit(market_view)
            except Exception as err:
                print(err)
                pass
    def __init__(self):
        self.mp = karmamarket.Marketplace()
        self.mp._load()
        self.reddit = praw.Reddit("bot1")
        print(dir(self.reddit))
        self.updanda_dict = {}
        for m in self.mp.markets:
            self.updanda_dict[m] = {"submission": None, "comments": []}
            split = m.comments.split(";")
            for s in split:
                # is a submission
                if s.startswith("t3"):
                    submission = self.reddit.submission(id=s[3:])
                    self.updanda_dict[m]["submission"] = submission
                elif s.startswith("t1"):
                    try:
                        comment = self.reddit.comment(id=s[3:])
                        print(comment)
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
