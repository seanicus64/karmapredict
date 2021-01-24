#!/usr/bin/env python3
import os
import shlex
import getopt
import discord
import parsedatetime as pdt

cal = pdt.Calendar()
from karmamarket import Marketplace
marketplace = Marketplace()
marketplace._load()
marketplace.autosave = True
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
client = discord.Client()
def create_player_embed(player):
    embed = discord.Embed(title="Player", color=0x8acc14)
    embed.add_field(name="Player", value=player)
    embed.add_field(name="Money", value=int(marketplace.bank[player]))
    return embed
def create_market_embed(market):
    embed = discord.Embed(title="Market")
        
    text = "```opt   name            cost    amount\n"
    embed = discord.Embed(title=market.text, color=0x8acc14)
    all_embeds.append(embed)
    labels = iter("abcdefghijklmnopqrstuvwxyz") 

    for s in market.stocks:
        print(s.text)
        print(s.cost)
        print(s.num_shares)
        text += f"{market.id}.{next(labels).upper()}: {s.text:<15}{s.cost:>3.2f}{s.num_shares:>10}\n"
    text += "```"
    embed.set_thumbnail(url="https://cdn.dribbble.com/users/31864/screenshots/3666062/free_logos_dribbble_ph.jpg?compress=1&resize=800x600")
    embed.add_field(name="Options", value=text, inline=False)
    return embed
#    await message.channel.send("", embed=embed)
#    break
def create_market_list_embed():
    embed = discord.Embed(title="All Markets", color=0x8acc14)
    string = "```"
    print(marketplace)
    for m in marketplace.markets:
        if m.is_open:
            string += "{:<7}{}: {} \n".format(m.category.short, m.id, m.text.strip())# m.text + "\n"
    string += "```"
    embed.add_field(name="List of Markets", value = string)
    return embed

@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")
@client.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f"Hi {member.name}, welcome to my discord server!")

embed = discord.Embed(title="embed title", color=0x8acc14)
embed.add_field(name="banana", value="is a fruit", inline=False)
options_list = (
    ("A", "0-**10K**     $24"),
    ("B", "10K-20K   $10"),
    ("C", "20K-30K   $11"),
    ("D", "30K-40L   $14"),
    ("E", "40K-50K    $10"),
    ("F", "50K-60K    $8"),
    ("G", "60K-70K    $7"),
    ("H", "70K-80K    $2"),
    ("I", "80K-90K    $2"),
    ("J", "90K-100K   $1"),
    ("K", ">100K     $19"))
embed.set_footer(text="will this work?")
all_embeds = []
response = "this is my response"
response = """
```
A. 0-10K     $24                   100
B. 10K-20K   $10                    90
C. 20K-30K   $11                    70
D. 30K-40L   $14                    50
E. 40K-50K   $10                    40
F. 50K-60K    $8                    40 
G. 60K-70K    $7                     6
H. 70K-80K    $2                     8
I. 80K-90K    $2                     4
J. 90K-100K   $1                     5
K. >100K     $19                    34```
"""

embed.add_field(name="34.__Bitcoin worth on January 1, 2022?__", value=response, inline=True)
def create_market_embed2(market):
    embed = discord.Embed(title = "Market")
    embed.add_field(name="Category", value = market.category.short)
    embed.add_field(name="Author", value = market.author)
    embed.add_field(name="b value", value = market.b)
    embed.add_field(name="id", value=market.id)
    embed.add_field(name="status", value="open" if market.is_open else "closed")

    embed.add_field(name="test", value = ":ballot_box_with_check:")
    embed.add_field(name="Text", value = market.text, inline=False)
    return embed
def create_make_new_market_embed(category, text, author):
    print(f"category is {marketplace.categories[0].short} - {id(marketplace.categories[0])}")
    for j in marketplace.categories[0].judges:
        print(f"Judge {j}")
    market = marketplace.new_market(text, author, category)
    for j in marketplace.categories[0].judges:
        print(f"Judge2 {j}")
    print(market.id)
    embed = create_market_embed2(market)
    return embed
#    embed = discord.Embed(title = "New Market created")
#    embed.add_field(name="category", value = category.long)
#    embed.add_field(name="text", value = question)
#    return embed
def parse_market_line(message):
    text = message.content
    author = message.author.name
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
        print(c, cat.short)
        print(type(c), type(cat.short))
        if cat.short.lower() == c.lower():
            c = cat
            print(f"c is now {c.short}, {type(c)}")
            break
    market_text = args[0]
    print("nnnnnnnnnnnnnnnnnnnnn")
    print(market_text, author, c, b, f"type(c): {type(c)}")
    print("nnnnnnnnnnnnnnnnnnnnnnn")
    market = marketplace.new_market(market_text, author, c, b=b)
    return market

    print(optlist, args) 

@client.event
async def on_message(message):
    split = message.content.split()
    if message.author == client.user:
        return
    if message.content == "me":
        embed = create_player_embed(message.author.name)
        await message.channel.send("", embed=embed)
    if message.content == "test":
        await message.channel.send("", embed=embed)
    if message.content == "a":
        embed.set_field_at(0, name="try", value="this")
    
    if split[0].lower() == "add_options":
        options = parse_add_options(message.content)
    if split[0].lower() == "new_market" and len(split) > 2:
        market = parse_market_line(message)
        embed = create_market_embed2(market)
        await message.channel.send("", embed=embed)
        
#        category = category = marketplace.categories[0]
#        for c in marketplace.categories:
#            if c.short.lower() == split[1].lower():
#                category = c
#                break
#        author = message.author.name
#        question = " ".join(split[2:]).strip()
#        embed = create_make_new_market_embed(category, question, author)
#        await message.channel.send("", embed=embed)
        

    if message.content.startswith("buy"):
        split = message.content.strip().split()
        # buy 32.B 8
        if len(split) == 3:
            market = None
            which_option = None
            amount = 0
            market = None
            for argument in split:
                if argument.isdigit():
                    amount = int(argument)
                if "." in argument:
#                if argument.contains("."):
                    market_cand, _, option_cand = argument.partition(".")
                    if not market_cand.isdigit():
                        continue
                    market_cand = int(market_cand)
                    for ma in marketplace.markets:
                        if market_cand == ma.id: 
                            market = ma
                            break
                    if not market:
                        print("there is no market")
                        continue
                    alphabet = "abcdefghijklmnopqrstuvwxyz"
                    alpha_iter = iter(alphabet)
                    
                    if option_cand.lower() not in alphabet:
                        print("{} is not in alphabet".format(option_card.lower()))
                        break
                    print(len(market.stocks))
                    for s in market.stocks:
                        current_letter = next(alpha_iter)
                        print(option_cand.lower(), current_letter)
                        if option_cand.lower() == current_letter:
                            which_option = s

            print("="*30)
            print(market.id, which_option, amount)
            print("^^^^^^^^^^^^")
            if not any((market, which_option, amount)):
                return
            which_option.buy(message.author.name, amount)
            embed = discord.Embed(title="Stock Purchase Receipt", color=0x8acc14)
            embed.add_field(name = "Player", value = message.author.name, inline=True)
            embed.add_field(name = "Stock", value = "{}.{}".format(ma.id, current_letter.upper()), inline=True)
            embed.add_field(name = "Amount", value = amount)
            await message.channel.send("", embed=embed)
            print("purchased")
    
    if message.content == "register":
        name = message.author.name
        success = marketplace.categories[0].add_judge(name)
        print(success)
        successfully_created = marketplace.create_new_player(name, 5000)
        #TODO: REMOVE ADD JUDGE
        if successfully_created:
            
            embed = discord.Embed(title="Created new user")
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(name="Cash", value=5000, inline=True)
        else:
            embed = discord.Embed(title="User already created")
        await message.channel.send("", embed=embed)

        #marketplace.register()
        pass 
    if len(split) == 2 and split[0] == "show" and split[1].isdigit():
        which_market = int(split[1])
        market = None
        for m in marketplace.markets:
            if m.id == which_market:
                market = m
                break
        if not market:
            return
        embed = create_market_embed(market)
        await message.channel.send("", embed=embed)
    if message.content == "list":
        await message.channel.send("", embed = create_market_list_embed())
#        create_market_list_embed()
        return
client.run(TOKEN)
pass
