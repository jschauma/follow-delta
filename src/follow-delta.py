#! /usr/bin/env python
#
# A dumb tool to list changes in twitter followship.
#
# Copyright (c) 2011, Jan Schaumann. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL <COPYRIGHT HOLDER> OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Originally written by Jan Schaumann <jschauma@netmeister.org> in March 2011.

import getopt
import os
import re
import sys
import tweepy

###
### Classes
###

class FollowDelta(object):
    """A Twitter Followship Diff generator."""

    EXIT_ERROR = 1
    EXIT_SUCCESS = 0

    def __init__(self):
        """Construct a Tweet object with default values."""

        self.__opts = {
                    "direction" : "both",
                    "user" : ""
                 }

        self.datadir = os.path.expanduser("~/.twitter/followship/")
        self.verbosity = 0


    class Usage(Exception):
        """A simple exception that provides a usage statement and a return code."""

        def __init__(self, rval):
            self.err = rval
            self.msg = 'Usage: %s [-hv] [-d up|down] -u user\n' % os.path.basename(sys.argv[0])
            self.msg += '\t-h          print this message and exit\n'
            self.msg += '\t-d up|down  go into given direction\n'
            self.msg += '\t-u user     generate delta for this user\n'
            self.msg += '\t-v          increase verbosity\n'


    def chunks(self, listdata, listsize):
        """Chunk a list, as found on http://pastebin.mozilla.org/1077629"""

        for i in range(0, len(listdata), listsize):
            yield listdata[i:i+listsize]


    def getFromFile(self, what, fname):
        """Get a list of things from a file.

        Returns:
            a list of strings following a "what: " string in the file
        """

        self.verbose("Getting '%s' from '%s'." % (what, fname), 2)
        try:
            f = file(fname)
        except IOError, e:
            sys.stderr.write("Unable to open file '%s': %s\n" % \
                                (fname, e.strerror))
            sys.exit(self.EXIT_ERROR)

        strings = []
        pattern = re.compile('^(?P<type>[^:]+): (?P<names>.+)')
        for line in f.readlines():
            line = line.strip()
            m = pattern.match(line)
            if m:
                type = m.group('type')
                if type == what:
                    names = m.group('names')
                    strings = names.split(',')

        return strings


    def getList(self, what, user):
        """Get a full list of things from the API.

        Returns:
            a sorted list of usernames, either followers or 'friends'
        """

        wanted = []

        self.verbose("Getting %s of '%s'." % (what, user), 2)
        if what == "followers":
            if self.getOpt("direction") == "up":
                return wanted
            func = tweepy.api.followers
        elif what == "friends":
            if self.getOpt("direction") == "down":
                return wanted
            func = tweepy.api.friends
        else:
            sys.stderr.write("Illegal value '%s' for getList.\n" % what)
            return wanted

        # We only get 100 at a time; our rate limits is 150 calls per
        # hour, and we have to redo the same for 'friends', too, so
        # let's do 70 calls only.  This means we can only get at most
        # 7K followers and this tools is thus not useful for really
        # popular accounts, but so be it.  Even an authorized app
        # would only be allowed 350 calls per hour, which wouldn't buy
        # us all that much either.  Checking the timeout and waiting
        # for that long is unreasonable as well -- for really popular
        # accounts that would mean we wait for days.

        num = 0
        threshold = 70
        if self.getOpt("direction") != "both":
            threshold = 140

        for page in tweepy.Cursor(func,screen_name=user).pages():
            wanted.extend([ str(u.screen_name) for u in page ])
            self.verbose("Added %d users (%d in total) from page #%d." % \
                            (len(page), len(wanted), num), 3)
            num = num + 1
            if (num > threshold):
                self.verbose("Reached my limit of %d users in %d pages. Sorry." % \
                                (len(wanted), num), 3)
                break

        wanted.sort()

        return wanted



    def printChunks(self, tweeters, n):
        """Print the given list of Tweepy.Users objects in chunks."""

        chunks = list(self.chunks(tweeters, n))
        for l in chunks:
            print "  " + ", ".join(l)


    def printDeltas(self, followers, old_followers, friends, old_friends):
        """Print the given lists containing the deltas."""

        user = self.getOpt("user")
        direction = self.getOpt("direction")
        new_followers = []
        gone_followers = []
        new_friends = []
        gone_friends = []

        if direction in [ "down", "both" ]:
            new_followers = list(set.difference(set(followers), set(old_followers)))
            gone_followers = list(set.difference(set(old_followers), set(followers)))

        if direction in [ "up", "both" ]:
            new_friends = list(set.difference(set(friends), set(old_friends)))
            gone_friends = list(set.difference(set(old_friends), set(friends)))

        self.verbose("Printing deltas (%d new followers, %d followers gone, %d new friends, %d friends gone)'." % \
            (len(new_followers), len(gone_followers),
             len(new_friends), len(gone_friends)), 2)

        if len(new_followers):
            print "%s is now followed by %d new users:" % (user, len(new_followers))
            self.printChunks(new_followers, 6)

        if len(gone_followers):
            print "%s is no longer followed by %d users:" % (user, len(gone_followers))
            self.printChunks(gone_followers, 6)

        if len(new_friends):
            print "%s is now following %d new users:" % (user, len(new_friends))
            self.printChunks(new_friends, 6)

        if len(gone_friends):
            print "%s is no longer following %d users:" % (user, len(gone_friends))
            self.printChunks(gone_friends, 6)



    def diffAndWrite(self, followers, friends):
        """Generate a diff to stdout, then write the full list to the
            file."""

        user = self.getOpt("user")
        ufile = self.datadir + user

        old_followers = []
        old_friends = []

        self.verbose("Diffing followship of '%s'." % user)

        if not os.path.exists(self.datadir):
            self.verbose("Creating datadir '%s'.\n" % self.datadir, 3)
            os.makedirs(self.datadir)

        if not os.path.exists(ufile):
            self.verbose("'%s' does not exist." % ufile, 3)
            self.printDeltas(followers, [], friends, [])

        else:
            self.verbose("Getting old followship for '%s'." % user, 2)
            old_followers = self.getFromFile("followers", ufile)
            old_friends = self.getFromFile("friends", ufile)
            self.printDeltas(followers, old_followers, friends, old_friends)

        # if we're not going in both directions, then we're not updating
        # the full followship
        direction = self.getOpt("direction")
        if direction == "up":
            friends = old_friends
        if direction == "down":
            followers = old_followers

        self.writeFollowship(ufile, followers, friends)



    def generateDelta(self):
        """Generate the full delta.

           If we have never seen the user, fetch the full list, display it
           and write it out.
           Otherwise, fetch the full list, diff to what's in the file,
           display the diff and write the new list to the file.
        """

        user = self.getOpt("user")

        followers = []
        friends = []

        try:
            self.verbose("Getting followship of '%s'." % user)
            followers = self.getList("followers", user)
            friends = self.getList("friends", user)

            self.diffAndWrite(followers, friends)

        except tweepy.error.TweepError, e:
            # http://apiwiki.twitter.com/w/page/22554652/HTTP-Response-Codes-and-Errors
            if e.response.status == 400:
                import time
                t1 = time.time()
                t2 = tweepy.api.rate_limit_status()['reset_time_in_seconds']
                time_diff = t2 - t1
                minutes = int(time_diff/60.0)
                seconds = int(time_diff%60.0)
                plural = ""
                if (minutes != 1):
                    plural = "s"
                sys.stderr.write("Rate throttling in effect. Try again in %s minute%s and %s seconds.\n" % \
                                (minutes, plural, seconds))
                sys.stderr.write("Try again at %s.\n" % time.ctime(tweepy.api.rate_limit_status()['reset_time_in_seconds']))


    def getOpt(self, opt):
        """Retrieve the given configuration option.

        Returns:
            The value for the given option if it exists, None otherwise.
        """

        try:
            r = self.__opts[opt]
        except ValueError:
            r = None

        return r


    def parseOptions(self, inargs):
        """Parse given command-line options and set appropriate attributes.

        Arguments:
            inargs -- arguments to parse

        Raises:
            Usage -- if '-h' or invalid command-line args are given
        """

        try:
            opts, args = getopt.getopt(inargs, "d:hu:v")
        except getopt.GetoptError:
            raise self.Usage(self.EXIT_ERROR)

        for o, a in opts:
            if o in ("-d"):
                if not a in [ "up", "down" ]:
                    sys.stderr.write("Invalid argument for '-d'.\n")
                    raise self.Usage(self.EXIT_ERROR)
                else:
                    self.setOpt("direction", a)
            if o in ("-h"):
                raise self.Usage(self.EXIT_SUCCESS)
            if o in ("-u"):
                self.setOpt("user", a)
            if o in ("-v"):
                self.verbosity = self.verbosity + 1

        if not self.getOpt("user") or args:
            raise self.Usage(self.EXIT_ERROR)


    def setOpt(self, opt, val):
        """Set the given option to the provided value"""

        self.__opts[opt] = val


    def verbose(self, msg, level=1):
        """Print given message to STDERR if the object's verbosity is >=
           the given level"""

        if (self.verbosity >= level):
            sys.stderr.write("%s> %s\n" % ('=' * level, msg))


    def writeFollowship(self, ufile, followers, friends):
        """Write the followship to the file."""

        try:
            f = file(ufile, "w")
            f.write("followers: " + ",".join(followers) + "\n")
            f.write("friends: " + ",".join(friends) + "\n")
            f.close()
        except IOError, e:
            sys.stderr.write("Unable to write to '%s': %s\n" % \
                (ufile, e.strerror))
            raise

###
### "Main"
###

if __name__ == "__main__":
    try:
        fd = FollowDelta()
        try:
            fd.parseOptions(sys.argv[1:])
            fd.generateDelta()

        except fd.Usage, u:
            if (u.err == fd.EXIT_ERROR):
                out = sys.stderr
            else:
                out = sys.stdout
            out.write(u.msg)
            sys.exit(u.err)
	        # NOTREACHED

    except KeyboardInterrupt:
        # catch ^C, so we don't get a "confusing" python trace
        sys.exit(FollowDelta.EXIT_ERROR)
