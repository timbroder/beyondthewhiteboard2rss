from BeautifulSoup import BeautifulSoup
import webapp2
import urllib2
import PyRSS2Gen
import datetime
import cgi
from google.appengine.ext import db
import logging

class WodEntry(db.Model):
    user_id = db.IntegerProperty()
    workout_url = db.StringProperty()
    session_url = db.StringProperty()
    workout_name = db.StringProperty()
    workout_desc = db.TextProperty()
    workout_details = db.TextProperty()
    result = db.TextProperty()
    date = db.DateTimeProperty()
    notes = db.TextProperty()

    def desc(self):
        ret = "<h2>Workout</h2>%s<h2>Result - %s</h2>%s<br/><br/>%s" % (
                self.workout_desc,
                self.date.strftime('%b, %d %Y'),
                self.result,
                self.workout_details.replace("NA</span>", "</span>"))
        if self.notes:
            ret = "%s<br/><br/><h2>Notes</h2>%s<br/><br/>" % (ret, self.notes)
        ret = """%s<br/>Powered by
                <a href=\"http://beyondthewhiteboard2rss.timbroder.com/\"
                target=\"_blank\">beyondthewhiteboard2rss</a>""" % ret
        return ret


class Main(webapp2.RequestHandler):
    header = """
                <html>
                    <head>
                        <script type="text/javascript">
                            var _gaq = _gaq || [];
                            _gaq.push(['_setAccount', 'UA-17099661-2']);
                            _gaq.push(['_trackPageview']);
                        
                            (function() {
                                var ga = document.createElement('script');
                                ga.type = 'text/javascript'; ga.async = true;
                                ga.src = ('https:' == document.location.protocol
                                    ? 'https://ssl' : 'http://www')
                                    + '.google-analytics.com/ga.js';
                                var s = document.getElementsByTagName('script')[0];
                                s.parentNode.insertBefore(ga, s);
                          })();
                        
                        </script>
                        <script src="http://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/2.0.2/bootstrap.min.js"></script>
                        <link href="http://twitter.github.com/bootstrap/1.4.0/bootstrap.min.css" rel="stylesheet">
                        <style>
                          body {
                            padding-top: 60px; /* 60px to make the container go all the way to the bottom of the topbar */
                          }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Beyond The Whiteboard 2 RSS</h1>
                    """

    footer = """
                            <p><i>This site is not affiliated with or endorsed by
                            beyondthewhiteboard.com</i></p></body>
                        </div>
                    </html>"""

    def get(self):
        img = "http://farm8.staticflickr.com/7035/6669670393_a789421208_o.png"
        body = """
                  <h4>Get an RSS feed of the workouts you log.  More features coming soon</h4>
                  <p>Enter your beyondthewhiteboard id (see screenshot on where to find it)</p>
                  <form action="/" method="post"></p>
                    <p><input type="text" name="btwbid" class="span3" style="height:30px"></p>
                    <p><button type="submit" class="btn">Submit</button></p>
                  </form>
                  <p><img
                      src="%s"
                      alt="finding your beyondthewhiteboard id" border="1"></p>
                    """ % img
        html = "%s%s%s" % (self.header, body, self.footer)

        self.response.out.write(html)

    def post(self):
        html = "%s<p>Wod Rss: <a href=\"/wods/%s/\">Click Here</a>%s"

        self.response.out.write(html % (self.header, cgi.escape(self.request.get('btwbid')), self.footer))


class Wods(webapp2.RequestHandler):
    site = "http://beyondthewhiteboard.com"
    timsite = "http://beyondthewhiteboard2rss.timbroder.com"

    def soup_url(self, url):
        logging.info('!!!' + url + '!!!')

        response = urllib2.urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html)

        return soup

    def workout_details(self, url):
        try:
            workout = self.soup_url(url)
        except urllib2.HTTPError:
            return "Workout information is not public<br>Click <a href=\"%s\">here</a> to see.<br><br>" % url
        return workout.find(
                'div', {'class': 'workout_description_container'})

    def entry_rss(self, entry):
        rss_entry = PyRSS2Gen.RSSItem(
                          title=entry.workout_name,
                          link=entry.session_url,
                          description=entry.desc(),
                          pubDate=entry.date
                          )
        return rss_entry

    def workout_post(self, url, id):
        query = WodEntry.all().filter("session_url =", url)

        if query.count() > 0:
            return self.entry_rss(query[0])
            pass
        else:
            soup = self.soup_url(url)
            table = soup.find('table', {'class': 'workout_session_table'})
            trs = table.findAll('tr')

            workout_url = trs[0].find('a')
            workout_url['href'] = "%s%s" % (self.site, workout_url['href'])
            workout_desc = self.workout_details(workout_url['href'])

            workout_details = soup.findAll('div', {'class': 'section'})[1]
            for href in workout_details.findAll('a'):
                href['href'] = "%s%s" % (self.site, href['href'])

            result = trs[1].find('strong').string.strip()
            completed_date = trs[2].findAll('td')[2].string.strip()
            try:
                notes = trs[3].findAll('td')[2].string.strip()
            except:
                notes = None
                pass

            #print "Workout Name: %s" % workout_url.string.strip()
            #print "Workout url: %s" % workout_url['href']
            #print workout_desc
            #print "Result: %s" % result
            #print "Date: %s" % completed_date
            #print "Notes: %s" % notes
            entry = WodEntry()
            entry.user_id = int(id)
            entry.workout_url = "%s".decode("utf-8") % workout_url['href']
            entry.workout_name = "%s".decode(
                "utf-8") % workout_url.string.strip()
            entry.workout_desc = "%s".decode("utf-8") % workout_desc
            entry.workout_details = "%s".decode("utf-8") % workout_details
            entry.result = "%s".decode("utf-8") % result
            entry.date = datetime.datetime.strptime(
                completed_date, '%A, %B %d, %Y')
            entry.notes = "%s".decode("utf-8") % notes
            entry.session_url = "%s".decode("utf-8") % url
            entry.put()
            return self.entry_rss(entry)

    def workout_posts(self, id):
        soup = self.soup_url(
            "%s/members/%s/workout_sessions" % (self.site, id))
        user = soup.find('div', {'class': 'name group'}
            ).find('a').string.strip()
        entries = []
        groups = soup.findAll('dl',
            {'class': 'workout_session activity group'})
        for group in groups:
            wod_url = "http://beyondthewhiteboard.com%s" % group.find(
                'span', {'class': 'title_session_result'}
                ).find('a')['href']
            entries.append(self.workout_post(wod_url, id))
            #break

        rss = PyRSS2Gen.RSS2(
                             title="%s's Workouts" % user,
                             link="%s/wods/%s" % (self.timsite, id),
                             description="RSS Description",
                             lastBuildDate=datetime.datetime.now(),
                             items=entries
                             )
        self.response.headers['Content-Type'] = "text/xml; charset=utf-8"
        self.response.out.write(rss.to_xml())

    def get(self, id):
        self.workout_posts(id)

app = webapp2.WSGIApplication([
                               ('/', Main),
                               ('/wods/(\d+)/', Wods)
                               ],
                               debug=True)
