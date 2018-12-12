from sys import exc_info
import text_manipulators
from datetime import datetime, timedelta
# global conn set by reload_function

# Corresponds to the listbanners command
# Callable from DMs and Channels
# Dumps records from the sentinel table less than 30 days old
def listbanners_function(message, client, args):
    try:
        global conn
        cur = conn.cursor()
        cur.execute("SELECT id, name, description, created, triggered, lastmodified, subscribers, triggercount FROM sentinel WHERE lastmodified > NOW() - INTERVAL '30 days';")
        sentuple = cur.fetchone()
        bannerMessage = "Banner List:\n"
        while sentuple:
            bannerName = text_manipulators.smallcaps(sentuple[1])
            if bannerName is None or bannerName.strip() == "" or " " in bannerName:
                bannerName = "Banner {}".format(str(sentuple[0]))
            bannerMessage = bannerMessage + "**{}** ".format(bannerName)
            if sentuple[2]:
                bannerMessage = bannerMessage + sentuple[2]
            supporterPluralized = "supporters"
            if len(sentuple[6]) == 1:
                supporterPluralized = "supporter"
            goalAchievedVerb = "is"
            if sentuple[4]:
                goalAchievedVerb = "was"
            bannerMessage = bannerMessage + "\n{} {} · goal {} {}\nMᴀᴅᴇ: {}\n".format(str(len(sentuple[6])), supporterPluralized, goalAchievedVerb, str(sentuple[7]), sentuple[3].strftime("%Y-%m-%d %H:%M") + " (" + text_manipulators.pretty_date(sentuple[3]) + ")")
            if sentuple[4]:
                bannerMessage = bannerMessage + "Mᴇᴛ: {}\n".format(sentuple[4].strftime("%Y-%m-%d %H:%M") +  " (" + text_manipulators.pretty_date(sentuple[4]) + ")")
            sentuple = cur.fetchone()
            if sentuple:
                bannerMessage = bannerMessage + "──────────\n"
        conn.commit()
        bammerMessage = bannerMessage.rstrip()
        if bannerMessage:
            return bannerMessage
        else:
            return "No banners modified within the last 30 days. Raise a sentinel with `!assemble`"
    except Exception as e:
        if cur is not None:
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        print("LBF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

# Corresponds to the assemble command
# Callable from DMs and Channels
# Builds a record in the sentinel table, fails if it already exists
async def assemble_function(message, client, args):
    try:
        global conn
        bannerId = None
        bannerName = None
        triggerCount = None
        bannerDescription = None
        nameAutoGenerated = True
        cur = conn.cursor()
        try:
            triggerCount = int(args[0])
            bannerName = " ".join(args[1:])
            bannerDescription = bannerName
        except ValueError:
            triggerCount = int(args[1])
            bannerName = args[0]
            nameAutoGenerated = False
            bannerDescription =  " ".join(args[2:])
            pass
        cur.execute("INSERT INTO sentinel (name, description, lastModified, triggerCount) VALUES (%s, %s, %s, %s);", [bannerName, bannerDescription, datetime.now(), triggerCount])
        cur.execute("SELECT id FROM sentinel WHERE name = %s", [bannerName])
        bannerId = cur.fetchone()[0]
        conn.commit()
        if nameAutoGenerated:
            return await message.channel.send('Banner created! `!pledge {}` to commit to this pledge.'.format(str(bannerId)))
        else:
            return await message.channel.send('Banner created! `!pledge {}` to commit to this pledge.'.format(bannerName))
    except Exception as e:
        if cur is not None:
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        print("ABF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

# Corresponds to the pledge command
# Callable from DMs and Channels
# Requires sentinel record to exist
async def pledge_function(message, client, args):
    try:
        global conn
        bannerId = None
        sentuple = None
        cur = conn.cursor()
        try:
            cur.execute("SELECT id FROM sentinel WHERE id = %s LIMIT 1;", [int(args[0])])
            sentuple = cur.fetchone()
        except ValueError:
            pass
        if sentuple == None:
            cur.execute("SELECT COUNT(id) FROM sentinel WHERE name ILIKE %s;", [" ".join(args)])
            availableSentinels = cur.fetchone()[0]
            if availableSentinels == 0:
                conn.commit()
                return await message.channel.send('No banner "{}" available. Try `!assemble [critical number of subscribers] {}` to create one.'.format(args[0], " ".join(args)))
            elif availableSentinels == 1:
                cur.execute("SELECT id FROM sentinel WHERE name ILIKE %s;", [" ".join(args)])
                sentuple = cur.fetchone()
            elif availableSentinels > 1:
                conn.commit()
                return await message.channel.send('Not sure what you want to do: {} banners found containing {} in the name.'.format(str(availableSentinels), " ".join(args)))
        bannerId = sentuple[0]
        cur.execute("SELECT COUNT(id) FROM sentinel WHERE id = %s AND %s = ANY (subscribers);", [bannerId, message.author.id])
        if cur.fetchone()[0]:
            conn.commit()
            return await message.channel.send('You already committed to this banner. `!defect {}` to defect.'.format(" ".join(args)))
        else:
            cur.execute("UPDATE sentinel SET subscribers = array_append(subscribers, %s), lastmodified = CURRENT_TIMESTAMP WHERE id = %s;", [message.author.id, bannerId])
            cur.execute("SELECT array_length(subscribers, 1), triggercount, name, subscribers, triggered FROM sentinel WHERE id = %s;", [bannerId])
            bannerInfo = cur.fetchone()
            if bannerInfo[0] == bannerInfo[1]: # Triggered banner! Yay!
                cur.execute("UPDATE sentinel SET triggered = CURRENT_TIMESTAMP WHERE id = %s;", [bannerId])
                conn.commit()
                return await message.channel.send('Critical mass reached for banner {}! Paging supporters: <@{}>. Now it\'s up to you to fulfill your goal :)'.format(bannerInfo[2], ">, <@".join([str(userId) for userId in bannerInfo[3]])))
            elif bannerInfo[0] > bannerInfo[1]:
                conn.commit()
                return await message.channel.send('Critical mass was reached for banner {} at {}! You are the {} supporter.'.format(bannerInfo[2], bannerInfo[4].strftime("%Y-%m-%d %H:%M:%S"), ordinal(bannerInfo[0])))
            else:
                conn.commit()
                return await message.channel.send('You pledged your support for banner {} (one of {} supporters). It needs {} more supporters to reach its goal.'.format(bannerInfo[2], bannerInfo[0], str(bannerInfo[1] - bannerInfo[0])))
    except Exception as e:
        if cur is not None:
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        print("PBF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))

# Corresponds to the defect command
# Callable from DMs and Channels
# Requires sentinel record to exist
async def defect_function(message, client, args):
    try:
        global conn
        bannerId = None
        sentuple = None
        cur = conn.cursor()
        try:
            cur.execute("SELECT id FROM sentinel WHERE id = %s LIMIT 1;", [int(args[0])])
            sentuple = cur.fetchone()
        except ValueError:
            pass
        if sentuple == None:
            cur.execute("SELECT COUNT(id) FROM sentinel WHERE name ILIKE %s;", [" ".join(args)])
            availableSentinels = cur.fetchone()[0]
            if availableSentinels == 0:
                conn.commit()
                return await message.channel.send('No banner "{}" available. Try `!assemble [critical number of subscribers] {}` to create one.'.format(args[0], " ".join(args)))
            elif availableSentinels == 1:
                cur.execute("SELECT id FROM sentinel WHERE name ILIKE %s;", [" ".join(args)])
                sentuple = cur.fetchone()
            elif availableSentinels > 1:
                conn.commit()
                return await message.channel.send('Not sure what you want to do: {} banners found containing {} in the name.'.format(str(availableSentinels), " ".join(args)))
        bannerId = sentuple[0]
        cur.execute("SELECT COUNT(id) FROM sentinel WHERE id = %s AND %s = ANY (subscribers);", [bannerId, message.author.id])
        if cur.fetchone()[0]:
            cur.execute("SELECT array_length(subscribers, 1), triggercount, name, subscribers FROM sentinel WHERE id = %s;", [bannerId])
            bannerInfo = cur.fetchone()
            if bannerInfo[0] >= bannerInfo[1]: # Triggered banner, can't go back now
                conn.commit()
                return await message.channel.send('Critical mass reached for banner {}! You can\'t defect anymore.'.format(bannerInfo[2]))
            else:
                cur.execute("UPDATE sentinel SET subscribers = array_remove(subscribers, %s), lastmodified = CURRENT_TIMESTAMP WHERE id = %s;", [message.author.id, bannerId])
                conn.commit()
                return await message.channel.send('You defected from banner {}. It now needs {} more supporters to reach its goal.'.format(bannerInfo[2], str(bannerInfo[1] - bannerInfo[0])))
        else:
            conn.commit()
            return await message.channel.send('You have not committed to this banner. `!pledge {}` to pledge support.'.format(" ".join(args)))
    except Exception as e:
        if cur is not None:
            conn.rollback()
        exc_type, exc_obj, exc_tb = exc_info()
        print("DBF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))
