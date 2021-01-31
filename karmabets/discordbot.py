#!/usr/bin/env python3
import os
import shlex
import getopt
import discord
import parsedatetime as pdt
from operator import itemgetter
from karmamarket import Marketplace
from dotenv import load_dotenv
cal = pdt.Calendar()
marketplace = Marketplace()
marketplace._load()
marketplace.autosave = True
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
client = discord.Client()

def create_error_embed(error):
    embed = discord.Embed(title="Error", color=0xff0000)
    embed.add_field(name="Message", value=error)
    return embed

def create_player_embed(player):
    """Create an embed for player's info"""
    share_list = []
    for market in marketplace.markets:
        alphabet = iter("abcdefghijklmnopqrstuvwxyz")
        if not market.is_open:
            continue
        for stock in market.stocks:
            label = next(alphabet)
            for player, s_dict in stock.shares.items():
                amount = s_dict["amount"]
                cost = s_dict["cost"]
                stock_text = stock.text
                if len(stock.text) >= 25:
                    stock_text = stock.text[:25] + "..."
                share_list.append((f"{market.id}.{label.upper()}", stock_text, amount, f"${int(cost)}"))
                #share_list.append(f"{market.id}.{label}    {amount}    ${int(cost)}")
    sorted_list = reversed(sorted(share_list, key=itemgetter(2)))
    share_string = "```Opt   Amt   Cost  Option Text\n"
    for s in sorted_list:
        share_string += f"{s[0]:<3}  {s[2]:>4}{s[3]:>7}  {s[1]:<10}\n"
    share_string += "```"
    if not share_list: share_string = "No shares currently owned"
    embed = discord.Embed(title="Player", color=0x8acc14)
    embed.add_field(name="Player", value=player)
    embed.add_field(name="Money", value="$" + str(int(marketplace.bank[player])))
    embed.add_field(name="Shares", value=share_string, inline=False)

    return embed

def create_market_embed(market):
    """Create an embed show a market"""
    embed = discord.Embed(title="Market")
#    text = "```opt   name            cost    amount\n"
    embed = discord.Embed(title=market.text, color=0x8acc14)
    labels = iter("abcdefghijklmnopqrstuvwxyz") 
#    for s in market.stocks:
#        text += f"{market.id}.{next(labels).upper()}: {s.text[:30]:<30}{s.cost:>3.2f}{s.num_shares:>10}\n"
#    text += "```"
    share_string = "```Opt   Amt   Cost  Option Text\n"
    for s in market.stocks:
        
        share_string += f"{market.id}.{next(labels).upper()}: {s.num_shares:>4}{'$'+str(int(s.cost)):>7}  {s.text:<10}\n"
    share_string += "```"
    embed.add_field(name="Status", value="Open" if market.is_open else "Closed", inline=True)
    embed.add_field(name="ID", value=market.id, inline=True)
    embed.add_field(name="Creator", value=market.author, inline=True)
    embed.add_field(name="Options", value=share_string, inline=False)
    return embed

def create_help_embed():
    
    help_text =  "Prediction market. Buy shares of options you think are likely to occur, "
    help_text += "sell shares of options you think are not likely to occur. "
    help_text += "Share values adjust according to Robin Hanson's **Logarithmic Market Scoring Rule Market Maker** "
    help_text += "(LMSR).  If an option is called, each holder of the share is paid out $100 for each share held. \n"
    help_text += "In theory, the cost of each share reflects the actual percentage chance of an event happening.\n"
    cmd_text = "```"
    cmd_text += "$buy <market_id>.<option_label> [amount] \n\t- Buy multiple shares of an option. Defaults to 1.\n"
    cmd_text += "$sell <market_id>.<option_label> [amount] \n\t- Sell multiple shares of an option. Defaults to 1.\n"
    cmd_text += "$show <market_id> - Shows information about a market.\n"
    cmd_text += "$list - Shows all open shares\n"
    cmd_text += "$me - Shows information about yourself\n"
    cmd_text += "$help - Shows this help text```"
    embed = discord.Embed(title="Help")
    embed.add_field(name="Information", value=help_text, inline=False)
    embed.add_field(name="Commands", value=cmd_text, inline=False)
    return embed

def create_delete_market_embed(market):
    """Create an embed confirming the deletion of a market."""
    marketplace.delete_market(market)
    embed = discord.Embed(title="Delete Market")
    embed.add_field(name="Successful", value=True)
    return embed

def create_market_list_embed():
    """Create a market showing all open markets."""
    embed = discord.Embed(title="All Markets", color=0x8acc14)
    string = "```"
    for m in marketplace.markets:
        if m.is_open:
            string += "{:<7}{}: {} \n".format(m.category.short, m.id, m.text.strip())# m.text + "\n"
    string += "```"
    embed.add_field(name="List of Markets", value = string)
    return embed

def create_market_resolved_embed(market):
    letters = iter("abcdefghijklmnopqrstuvwxyz")
    correct = None
    for s in market.stocks:
        label = next(letters)
        if s.is_correct:
            correct = s
            break
    if not correct: return False
            
    embed = discord.Embed(title="Market resolved", color=0x8acc14)
    embed.add_field(name="Market ID", value=market.id)
    embed.add_field(name="Text", value=market.text)
    embed.add_field(name="Correct option", value=f"{label}: {s.text})")
    return embed

def parse_market_line(message):
    """Parses the commandline to create a new market, 
    returns resultant market"""
    text = message.content
    author = get_player_id(message.author)
    args = shlex.split(text)
    optlist, args = getopt.getopt(args[1:], "b:c:d:")
    b = 100
    c = "MISC"
    d = cal.parse("One year")
    for k, v in optlist:
        if k == "-b":
            b = int(v)
        elif k == "-c":
            c = v
        elif k == "-d":
            d = cal.parse(v)
    for cat in marketplace.categories:
        if cat.short.lower() == c.lower():
            c = cat
            break
    market_text = args[0]
    market = marketplace.new_market(market_text, author, c, b=b)
    return market

def parse_add_options(message):
    """Parses an add_options command."""
    split = message.content.split()
    market = None
    market_id = split[1]
    if split[1].isdigit():
        market_id = int(split[1])
        market = marketplace.get_market(market_id)
    if not market:
        raise Exception(f"Market '{market_id}' does not exist.")
    if market.is_open:
        raise Exception(f"Market '{market_id}' is already open")
    split_lines = message.content.split("\n")
    if len(split_lines) <= 1:
        raise Exception("No options given")
    for l in split_lines[1:]:
        market.add_option(l)
    return market
    
def get_player_id(author):
    """Creates a key for the marketplace bank dictionary, and returns it"""
    return f"{author.name}#{author.discriminator}"

@client.event
async def on_ready():
    """Handles what happens when bot first joins."""
    print(f"{client.user} has connected to Discord!")

@client.event
async def on_member_join(member):
    """Handles what happens when a new member joins."""
    pass

@client.event
async def on_message(message):
    player_id = get_player_id(message.author)
    if player_id not in marketplace.bank.keys():
        successfully_created = marketplace.create_new_player(player_id, 5000)
        print(f"Created new player: {player_id}")
   
    split = message.content.split()
    name = get_player_id(message.author)
    if message.author == client.user:
        return
   
    if message.content == "$me":
        embed = create_player_embed(name)
        await message.channel.send("", embed=embed)
    
    if len(split) == 2 and split[0].lower() == "$open" and split[1].isdigit():
        market_id = int(split[1])
        market = marketplace.get_market(market_id)
        if not market:
            return
        market.open()
        embed = create_market_embed(market)
        await message.channel.send("", embed=embed)

    if split[0].lower() == "$help":
        embed = create_help_embed()
        await message.channel.send("", embed=embed)

    if split[0].lower() in ("$add_options", "$add_option", "$ao"):
        try:
            market = parse_add_options(message)
        except Exception as e:
            embed = create_error_embed(e.args[0])
            await message.channel.send("", embed=embed)
            return False
        embed = create_market_embed(market)
        await message.channel.send("", embed=embed)
        return True

    if split[0].lower() == "$call" and len(split) >= 2:
        correct_option = split[1]
        if "." not in correct_option:
            error_text = "Invalid argument; must be in form of '<market_id>.<option_label>'"
            error_text += "\n example: '55.C'"
            embed = make_error_embed(error_text)
            await message.channel.send("", embed=embed)
            return False
        parts = correct_option.partition(".")
        market_id = parts[0]
        option_id = parts[2].lower()
        try:
            assert market_id.isdigit()
            market_id = int(market_id)
        except:
            error_text = "Invalid argument; must be in form of '<market_id>.<option_label>'"
            error_text += "\n example: '55.C'"
            embed = make_error_embed(error_text)
            await message.channel.send("", embed=embed)
            return False
        market = marketplace.get_market(market_id)
        if not market: 
            error_text = "Invalid market"
            embed = make_error_embed(error_text)
            await message.channel.send("", embed=embed)
            return False
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        alphabet = iter(alphabet)
        options = iter(market.stocks)
        option = None
        for letter in alphabet:
            this_option = next(options)
            if option_id == letter:
                option = this_option
                break
        if not option: 
            embed = make_error_embed("Invalid option '{option_id}' for market '{market_id}'")
            await message.channel.send("", embed=embed)
            return False
        if name not in market.category.judges:
            error_message = "'{name}' is not a judge for category '{market.category.short}'"
            embed = make_error_embed(error_message)
            await message.channel.send("", embed=embed)
            return False
        market.call(option)
        embed = create_market_resolved_embed(market)
        await message.channel.send("", embed=embed)
        return True

        
    if len(split) == 2 and split[0].lower() == "$delete_market" and split[1].isdigit():
        return False
        market_id = int(split[1])
        market = marketplace.get_market(market_id)

        if market:
            embed = create_delete_market_embed(market)
        else:
            embed = discord.Embed(title="Failed")
        await message.channel.send("", embed=embed)

    if split[0].lower() == "$new_market" and len(split) > 2:
        market = parse_market_line(message)
        embed = create_market_embed(market)
        await message.channel.send("", embed=embed)
        
    if split[0].lower() in ("$buy", "$sell"):
        split = message.content.strip().split()
        if len(split) >= 2:
            market = None
            which_option = None
            amount = 1
            market = None
            for argument in split:
                if argument.isdigit():
                    amount = int(argument)
                if "." in argument:
                    market_cand, _, option_cand = argument.partition(".")
                    if not market_cand.isdigit():
                        continue
                    market_cand = int(market_cand)
                    for ma in marketplace.markets:
                        if market_cand == ma.id: 
                            market = ma
                            break
                    if not market:
                        continue
                    alphabet = "abcdefghijklmnopqrstuvwxyz"
                    alpha_iter = iter(alphabet)
                    
                    if option_cand.lower() not in alphabet:
                        break
                    for s in market.stocks:
                        current_letter = next(alpha_iter)
                        if option_cand.lower() == current_letter:
                            which_option = s
                            break
            if not market.is_open:
                embed = create_error_embed(f"Market '{market.id}' is not open")
                await message.channel.send("", embed=embed)
                return False
            if not any((market, which_option, amount)):
                embed = create_error_embed(f"Malformed command")
                await message.channel.send("", embed=embed)
                return False
            before = int(marketplace.bank[name])
            try:
                if split[0].lower() == "$sell":
                    amount = -1 * amount
                which_option.buy(name, amount)
                embed = discord.Embed(title="Stock Purchase Receipt", color=0x8acc14)
                embed.add_field(name = "Player", value = name, inline=True)
                embed.add_field(name = "Stock", value = "{}.{}".format(ma.id, current_letter.upper()), inline=True)
                embed.add_field(name = "Amount", value = amount)
                embed.add_field(name = "Old amount", value = before)
                embed.add_field(name = "New amount", value = int(marketplace.bank[name]))
                await message.channel.send("test", embed=embed)
            except Exception as e:
                embed = create_error_embed(e.args[0])
    if len(split) == 2 and split[0] == "$show" and split[1].isdigit():
        market_id = int(split[1])
        market = marketplace.get_market(market_id)
        if not market:
            return
        embed = create_market_embed(market)
        await message.channel.send("", embed=embed)
    if message.content == "$list":
        await message.channel.send("", embed = create_market_list_embed())
        return
client.run(TOKEN)
