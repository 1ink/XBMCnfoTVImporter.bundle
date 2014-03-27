# XBMCnfoTVImporter
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
# Logo by CrazyRabbit
#
import os, re, time, datetime, platform, traceback, glob

class xbmcnfotv(Agent.TV_Shows):
	name = 'XBMCnfoTVImporter'
	version = '1.0-12-g29e7bc2-107'
	primary_provider = True
	languages = [Locale.Language.NoLanguage]
	accepts_from = ['com.plexapp.agents.localmedia','com.plexapp.agents.opensubtitles','com.plexapp.agents.podnapisi','com.plexapp.agents.plexthememusic']
	pc = '/';

##### helper functions #####
	def DLog (self, LogMessage):
		if Prefs['debug']:
			Log (LogMessage)

	def time_convert (self, duration):
		if (duration <= 2):
			duration = duration * 60 * 60 * 1000 #h to ms
		elif (duration <= 120):
			duration = duration * 60 * 1000 #m to ms
		elif (duration <= 7200):
			duration = duration * 1000 #s to ms
		return duration

	def checkFilePaths(self, pathfns, ftype):
		for pathfn in pathfns:
			self.DLog("Trying " + pathfn)
			if not os.path.exists(pathfn):
				continue
			else:
				Log("Found " + ftype + " file " + pathfn)
				return pathfn
		else:
			Log("No " + ftype + " file found! Aborting!")

	def RemoveEmptyTags(self, xmltags):
		for xmltag in xmltags.iter("*"):
			if len(xmltag):
				continue
			if not (xmltag.text and xmltag.text.strip()):
				#self.DLog("Removing empty XMLTag: " + xmltag.tag)
				xmltag.getparent().remove(xmltag)
		return xmltags

	def FloatRound(self, x):
		return x + 0.5 / 2 - ((x + 0.5 / 2) % 0.5)

##### search function #####
	def search(self, results, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering search function")
		self.DLog("++++++++++++++++++++++++")
		Log ("" + self.name + " Version: " + self.version)

		self.pc = '\\' if platform.system() == 'Windows' else '/'

		parse_date = lambda s: Datetime.ParseDate(s).date()
		self.DLog(media.primary_metadata)
		path1 = os.path.dirname(String.Unquote(media.filename).encode('utf-8'))
		self.DLog(path1)
		path = os.path.dirname(path1)
		nfoName = path + self.pc + "tvshow.nfo"
		self.DLog('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			nfoName = path1 + self.pc + "tvshow.nfo"
			self.DLog('Looking for TV Show NFO file at ' + nfoName)

		id = media.id
		year = 0
		title = None

		if not os.path.exists(nfoName):
			self.DLog("Couldn't find a tvshow.nfo file; will use the folder name as the TV show title:")
			title = os.path.basename(os.path.normpath(os.path.dirname(nfoName)))
			Log("Using tvshow.title = " + title)
		else:
			nfoFile = nfoName
			Log("Found nfo file at " + nfoFile)
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</tvshow>' % nfoText.split('</tvshow>')[0]
				
				#likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return
				Log(nfoXML.xpath("title"))
				
				# Title
				try: title = nfoXML.xpath("title")[0].text
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Year
				try: year = parse_date(nfoXML.xpath("premiered")[0].text).year
				except: pass
				# ID
				try: id = nfoXML.xpath("id")[0].text
				except:
					id = None

		# if tv show id doesn't exist, create
		# one based on hash of title
		if not id:
			ord3 = lambda x : '%.3d' % ord(x)
			id = int(''.join(map(ord3, title)))
			id = str(abs(hash(int(id))))
			
			Log('ID: ' + str(id))
			Log('Title: ' + str(title))
			Log('Year: ' + str(year))

		results.Append(MetadataSearchResult(id=id, name=title, year=year, lang=lang, score=100))
		Log('scraped results: ' + str(title) + ' | year = ' + str(year) + ' | id = ' + str(id))

##### update Function #####
	def update(self, metadata, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering update function")
		self.DLog("++++++++++++++++++++++++")
		Log ("" + self.name + " Version: " + self.version)

		self.pc = '\\' if platform.system() == 'Windows' else '/'

		Dict.Reset()
		metadata.duration = None
		id = media.id
		duration_key = 'duration_'+id
		Dict[duration_key] = [0] * 200
		Log('Update called for TV Show with id = ' + id)
		try: path1 = os.path.dirname(media.items[0].parts[0].file)
		except:
			pageUrl = "http://localhost:32400/library/metadata/" + id + "/tree"
			nfoXML = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MediaItem/MediaPart')[0]
			path1 = os.path.dirname(String.Unquote(nfoXML.get('file')))
		path = os.path.dirname(path1)
		parse_date = lambda s: Datetime.ParseDate(s).date()
		
		nfoName = path + self.pc + "tvshow.nfo"
		self.DLog('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			nfoName = path1 + self.pc + "tvshow.nfo"
			self.DLog('Looking for TV Show NFO file at ' + nfoName)
			path = path1
		if not os.path.exists(nfoName):
			path = os.path.dirname(path1)

		posterNames = []
		posterNames.append (path + self.pc + "poster.jpg")
		posterNames.append (path + self.pc + "folder.jpg")
		posterNames.append (path + self.pc + "show.jpg")
		posterNames.append (path + self.pc + "season-all-poster.jpg")

		# check possible poster file locations
		posterFilename = self.checkFilePaths (posterNames, 'poster')

		if posterFilename:
			posterData = Core.storage.load(posterFilename)
			metadata.posters['poster.jpg'] = Proxy.Media(posterData)
			Log('Found poster image at ' + posterFilename)

		bannerNames = []
		bannerNames.append (path + self.pc + "banner.jpg")
		bannerNames.append (path + self.pc + "folder-banner.jpg")

		# check possible banner file locations
		bannerFilename = self.checkFilePaths (bannerNames, 'banner')

		if bannerFilename:
			bannerData = Core.storage.load(bannerFilename)
			metadata.banners['banner.jpg'] = Proxy.Media(bannerData)
			Log('Found banner image at ' + bannerFilename)

		fanartNames = []

		fanartNames.append (path + self.pc + "fanart.jpg")
		fanartNames.append (path + self.pc + "art.jpg")
		fanartNames.append (path + self.pc + "backdrop.jpg")
		fanartNames.append (path + self.pc + "background.jpg")

		# check possible fanart file locations
		fanartFilename = self.checkFilePaths (fanartNames, 'fanart')

		if fanartFilename:
			fanartData = Core.storage.load(fanartFilename)
			metadata.art['fanart.jpg'] = Proxy.Media(fanartData)
			Log('Found fanart image at ' + fanartFilename)

		themeNames = []

		themeNames.append (path + self.pc + "theme.mp3")

		# check possible theme file locations
		themeFilename = self.checkFilePaths (themeNames, 'theme')

		if themeFilename:
			themeData = Core.storage.load(themeFilename)
			metadata.themes['theme.mp3'] = Proxy.Media(themeData)
			Log('Found theme music ' + themeFilename)

		if not os.path.exists(nfoName):
			self.DLog("Couldn't find a tvshow.nfo file; will use the folder name as the TV show title:")
			metadata.title = os.path.basename(os.path.normpath(os.path.dirname(nfoName)))
			self.DLog("Using tvshow.title = " + metadata.title)
		else:
			nfoFile = nfoName
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</tvshow>' % nfoText.split('</tvshow>')[0]

				#likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				#remove empty xml tags
				self.DLog('Removing empty XML tags from tvshows nfo...')
				nfoXML = self.RemoveEmptyTags(nfoXML)

				# Title
				try: metadata.title = nfoXML.xpath("title")[0].text
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Original Title
				try: metadata.original_title = nfoXML.xpath('originaltitle')[0].text
				except: pass
				# Rating
				try:
					rating = float(nfoXML.xpath("rating")[0].text.replace(',', '.'))
					if Prefs['fround']:
						metadata.rating = self.FloatRound(rating)
					else:
						metadata.rating = rating
				except: pass
				# Content Rating
				try:
					mpaa = nfoXML.xpath('./mpaa')[0].text
					match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaa)
					if match.group('mpaa'):
						content_rating = match.group('mpaa')
					else:
						content_rating = 'NR'
					metadata.content_rating = content_rating
				except: pass
				# Network
				try: metadata.studio = nfoXML.xpath("studio")[0].text
				except: pass
				# Premiere
				try:
					air_string = None
					try:
						self.DLog("Reading aired tag...")
						air_string = nfoXML.xpath("aired")[0].text
						self.DLog("Aired tag is: " + air_string)
					except:
						self.DLog("No aired tag found...")
						pass
					if not air_string:
						try:
							self.DLog("Reading premiered tag...")
							air_string = nfoXML.xpath("premiered")[0].text
							self.DLog("Premiered tag is: " + air_string)
						except:
							self.DLog("No premiered tag found...")
							pass
					if not air_string:
						try:
							self.DLog("Reading dateadded tag...")
							air_string = nfoXML.xpath("dateadded")[0].text
							self.DLog("Dateadded tag is: " + air_string)
						except:
							self.DLog("No dateadded tag found...")
							pass
					if air_string:
						metadata.originally_available_at = parse_date(air_string)
				except:
					self.DLog("Exception parsing Premiere: " + traceback.format_exc())
					pass
				# Tagline
				try: metadata.tagline = nfoXML.findall("tagline")[0].text
				except: pass
				# Summary (Plot)
				try: metadata.summary = nfoXML.xpath("plot")[0].text
				except: pass
				# Genres
				try:
					genres = nfoXML.xpath('genre')
					metadata.genres.clear()
					[metadata.genres.add(g.strip()) for genreXML in genres for g in genreXML.text.split("/")]
					metadata.genres.discard('')
				except: pass
				# Collections (Set)
				try:
					sets = nfoXML.xpath('set')
					metadata.collections.clear()
					[metadata.collections.add(s.strip()) for setXML in sets for s in setXML.text.split("/")]
					metadata.collections.discard('')
				except: pass
				# Duration
				try:
					sruntime = nfoXML.xpath("durationinseconds")[0].text
					metadata.duration = int(re.compile('^([0-9]+)').findall(sruntime)[0]) * 1000
				except:
					try:
						sruntime = nfoXML.xpath("runtime")[0].text
						duration = int(re.compile('^([0-9]+)').findall(sruntime)[0])
						duration_ms = xbmcnfotv.time_convert (self, duration)
						metadata.duration = duration_ms
						self.DLog("Set Series Episode Duration from " + str(duration) + " in tvshow.nfo file to " + str(duration_ms) + " in Plex.")
					except:
						self.DLog("No Series Episode Duration in tvschow.nfo file.")
						pass
				# Actors
				metadata.roles.clear()
				for actor in nfoXML.xpath('actor'):
					role = metadata.roles.new()
					try: role.role = actor.xpath("role")[0].text
					except: pass
					try: role.actor = actor.xpath("name")[0].text
					except: pass
					try: role.photo = actor.xpath("thumb")[0].text
					except: pass
					# if role.photo and role.photo != 'None' and role.photo != '':
						# data = HTTP.Request(actor.xpath("thumb")[0].text)
						# Log('Added Thumbnail for: ' + role.actor)
				
				
				Log("---------------------")
				Log("Series nfo Information")
				Log("---------------------")
				try: Log("ID: " + str(metadata.guid))
				except: Log("ID: -")
				try: Log("Title: " + str(metadata.title))
				except: Log("Title: -")
				try: Log("Original: " + str(metadata.original_title))
				except: Log("Original: -")
				try: Log("Rating: " + str(metadata.rating))
				except: Log("Rating: -")
				try: Log("Content: " + str(metadata.content_rating))
				except: Log("Content: -")
				try: Log("Network: " + str(metadata.studio))
				except: Log("Network: -")
				try: Log("Premiere: " + str(metadata.originally_available_at))
				except: Log("Premiere: -")
				try: Log("Tagline: " + str(metadata.tagline))
				except: Log("Tagline: -")
				try: Log("Summary: " + str(metadata.summary))
				except: Log("Summary: -")
				Log("Genres:")
				try: [Log("\t" + genre) for genre in metadata.genres]
				except: Log("\t-")
				Log("Collections:")
				try: [Log("\t" + collection) for collection in metadata.collections]
				except: Log("\t-")
				try: Log("Duration: " + str(metadata.duration // 60000) + ' min')
				except: Log("Duration: -")
				Log("Actors:")
				try: [Log("\t" + actor.actor + " > " + actor.role) for actor in metadata.roles]
				except: [Log("\t" + actor.actor) for actor in metadata.roles]
				except: Log("\t-")
				Log("---------------------")
				
		# Grabs the season data
		@parallelize
		def UpdateEpisodes():
			self.DLog("UpdateEpisodes called")
			pageUrl = "http://localhost:32400/library/metadata/" + media.id + "/children"
			seasonList = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Directory')

			seasons = []
			for seasons in seasonList:
				try: seasonID = seasons.get('key')
				except: pass
				try: season_num = seasons.get('index')
				except: pass
				
				self.DLog("seasonID : " + path)
				if seasonID.count('allLeaves') == 0:
					self.DLog("Finding episodes")

					pageUrl = "http://localhost:32400" + seasonID

					episodes = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Video')
					self.DLog("Found " + str(len(episodes)) + " episodes.")
					
					firstEpisodePath = XML.ElementFromURL(pageUrl).xpath('//Part')[0].get('file')
					seasonPath = os.path.dirname(firstEpisodePath)

					seasonFilename = ""
					seasonPathFilename = ""
					if(int(season_num) == 0):
						seasonFilenameFrodo = 'season-specials-poster.jpg'
						seasonFilenameEden = 'season-specials.tbn'
					else:
						seasonFilenameFrodo = 'season%(number)02d-poster.jpg' % {"number": int(season_num)}
						seasonFilenameEden = 'season%(number)02d.tbn' % {"number": int(season_num)}

					seasonPosterNames = []

					#Frodo
					seasonPosterNames.append (path + self.pc + seasonFilenameFrodo)
					seasonPosterNames.append (seasonPath + self.pc + seasonFilenameFrodo)
					#Eden
					seasonPosterNames.append (path + self.pc + seasonFilenameEden)
					seasonPosterNames.append (seasonPath + self.pc + seasonFilenameEden)
					#DLNA
					seasonPosterNames.append (seasonPath + self.pc + "folder.jpg")
					#Fallback to Series Poster
					seasonPosterNames.append (path + self.pc + "poster.jpg")

					# check possible season poster file locations
					seasonPosterFilename = self.checkFilePaths (seasonPosterNames, 'season poster')

					if seasonPosterFilename:
						seasonData = Core.storage.load(seasonPosterFilename)
						metadata.seasons[season_num].posters[seasonFilename] = Proxy.Media(seasonData)
						Log('Found season poster image at ' + seasonPosterFilename)

					episodeXML = []
					for episodeXML in episodes:
						ep_num = episodeXML.get('index')
						ep_key = episodeXML.get('key')
						self.DLog("Found episode with key: " + ep_key)
	
						# Get the episode object from the model
						episode = metadata.seasons[season_num].episodes[ep_num]

						# Grabs the episode information
						@task
						def UpdateEpisode(episode=episode, season_num=season_num, ep_num=ep_num, ep_key=ep_key, path=path1):
							self.DLog("UpdateEpisode called for episode S" + str(season_num.zfill(2)) + "E" + str(ep_num.zfill(2)))
							if(ep_num.count('allLeaves') == 0):
								pageUrl = "http://localhost:32400" + ep_key + "/tree"
								path1 = XML.ElementFromURL(pageUrl).xpath('//MediaPart')[0].get('file')
								self.DLog('UPDATE: ' + path1)
								filepath = path1.split
								path = os.path.dirname(path1)
								fileExtension = path1.split(".")[-1].lower()

								nfoFile = path1.replace('.'+fileExtension, '.nfo')
								self.DLog("Looking for episode NFO file " + nfoFile)
								if os.path.exists(nfoFile):
									self.DLog("File exists...")
									nfoText = Core.storage.load(nfoFile)
									# strip media browsers <multiepisodenfo> tags
									nfoText = nfoText.replace ('<multiepisodenfo>','')
									nfoText = nfoText.replace ('</multiepisodenfo>','')
									# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
									nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
									nfoTextLower = nfoText.lower()
									if nfoTextLower.count('<episodedetails') > 0 and nfoTextLower.count('</episodedetails>') > 0:
										nfoepc = nfoTextLower.count('<episodedetails')
										self.DLog("EPCount in nfo file: " + str(nfoepc))
										nfopos = int(ep_num)
										self.DLog("EPNum: " + str(nfopos))
										while nfopos > nfoepc: nfopos = nfopos - nfoepc
										self.DLog("EPNFOPos: " + str(nfopos))
										# Remove URLs (or other stuff) at the end of the XML file
										nfoText = '%s</episodedetails>' % nfoText.split('</episodedetails>')[nfopos-1]

										self.DLog("Looks like an XBMC NFO file (has <episodedetails>)")
										#likely an xbmc nfo file
										try: nfoXML = XML.ElementFromString(nfoText).xpath('//episodedetails')[0]
										except:
											self.DLog('ERROR: Cant parse XML in file: ' + nfoFile)
											return

										#remove empty xml tags
										self.DLog('Removing empty XML Tags from episode nfo...')
										nfoXML = self.RemoveEmptyTags(nfoXML)

										# Ep. Title
										try: episode.title = nfoXML.xpath('title')[0].text
										except:
											self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
											return
										# Ep. Content Rating
										try:
											mpaa = nfoXML.xpath('./mpaa')[0].text
											match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaa)
											if match.group('mpaa'):
												content_rating = match.group('mpaa')
											else:
												content_rating = 'NR'
											episode.content_rating = content_rating
										except: pass
										# Ep. Rating
										try:
											eprating = float(nfoXML.xpath("rating")[0].text.replace(',', '.'))
											if Prefs['fround']:
												episode.rating = self.FloatRound(eprating)
											else:
												episode.rating = eprating
										except: pass
										# Ep. Premiere
										try:
											air_string = None
											try:
												self.DLog("Reading aired tag...")
												air_string = nfoXML.xpath("aired")[0].text
												self.DLog("Aired tag is: " + air_string)
											except:
												self.DLog("No aired tag found...")
												pass
											if not air_string:
												try:
													self.DLog("Reading dateadded tag...")
													air_string = nfoXML.xpath("dateadded")[0].text
													self.DLog("Dateadded tag is: " + air_string)
												except:
													self.DLog("No dateadded tag found...")
													pass
											if air_string:
												episode.originally_available_at = parse_date(air_string)
										except:
											self.DLog("Exception parsing Ep Premiere: " + traceback.format_exc())
											pass
										# Ep. Summary
										try: episode.summary = nfoXML.xpath('plot')[0].text
										except: pass
										# Ep. Producers / Writers / Guest Stars(Credits)
										try:
											credit_string = None
											credits = nfoXML.xpath('credits')
											episode.producers.clear()
											episode.writers.clear()
											episode.guest_stars.clear()
											for creditXML in credits:
												for credit in creditXML.text.split("/"):
													credit_string = credit.strip()
													if "(Producer)" in credit_string:
														#self.DLog ("Credit (Producer): " + credit_string)
														episode.producers.add(credit_string.replace(" (Producer)",""))
													if "(Writer)" in credit_string:
														#self.DLog ("Credit (Writer): " + credit_string)
														episode.writers.add(credit_string.replace(" (Writer)",""))
													if "(Guest Star)" in credit_string:
														#self.DLog ("Credit (Guest Star): " + credit_string)
														episode.guest_stars.add(credit_string.replace(" (Guest Star)",""))
											episode.producers.discard('')
											episode.writers.discard('')
											episode.guest_stars.discard('')
										except: pass
										# Ep. Directors
										try: 
											directors = nfoXML.xpath('director')
											episode.directors.clear()
											[episode.directors.add(d.strip()) for directorXML in directors for d in directorXML.text.split("/")]
											episode.directors.discard('')
										except: pass
										# Ep. Duration
										try:
											self.DLog ("Trying to read <durationinseconds> tag from episodes .nfo file...")
											fileinfoXML = XML.ElementFromString(nfoText).xpath('fileinfo')[0]
											streamdetailsXML = fileinfoXML.xpath('streamdetails')[0]
											videoXML = streamdetailsXML.xpath('video')[0]
											eruntime = videoXML.xpath("durationinseconds")[0].text
											eduration_ms = int(re.compile('^([0-9]+)').findall(eruntime)[0]) * 1000
											episode.duration = eduration_ms
										except:
											try:
												self.DLog ("Fallback to <runtime> tag from episodes .nfo file...")
												eruntime = nfoXML.xpath("runtime")[0].text
												eduration = int(re.compile('^([0-9]+)').findall(eruntime)[0])
												eduration_ms = xbmcnfotv.time_convert (self, eduration)
												episode.duration = eduration_ms
											except:
												episode.duration = metadata.duration if metadata.duration else None
												self.DLog ("No Episode Duration in episodes .nfo file.")
												pass
										try:
											if (eduration_ms > 0):
												eduration_min = int(round (float(eduration_ms) / 1000 / 60))
												Dict[duration_key][eduration_min] = Dict[duration_key][eduration_min] + 1
										except:
											pass

										episodeThumbNames = []

										#Multiepisode nfo thumbs
										if nfoepc > 1:
											for name in glob.glob1(os.path.dirname(nfoFile), '*S' + str(season_num.zfill(2)) + 'E' + str(ep_num.zfill(2)) + '*.*'):
												if "-E" in name: continue
												episodeThumbNames.append (os.path.dirname(nfoFile) + self.pc + name)

										#Frodo
										episodeThumbNames.append (nfoFile.replace('.nfo', '-thumb.jpg'))
										#Eden
										episodeThumbNames.append (nfoFile.replace('.nfo', '.tbn'))
										#DLNA
										episodeThumbNames.append (nfoFile.replace('.nfo', '.jpg'))

										# check possible episode thumb file locations
										episodeThumbFilename = self.checkFilePaths (episodeThumbNames, 'episode thumb')

										if episodeThumbFilename:
											thumbData = Core.storage.load(episodeThumbFilename)
											episode.thumbs[episodeThumbFilename] = Proxy.Media(thumbData)
											Log('Found episode thumb image at ' + episodeThumbFilename)

										Log("---------------------")
										Log("Episode (S"+season_num.zfill(2)+"E"+ep_num.zfill(2)+") nfo Information")
										Log("---------------------")
										try: Log("Title: " + str(episode.title))
										except: Log("Title: -")
										try: Log("Content: " + str(episode.content_rating))
										except: Log("Content: -")
										try: Log("Rating: " + str(episode.rating))
										except: Log("Rating: -")
										try: Log("Premiere: " + str(episode.originally_available_at))
										except: Log("Premiere: -")
										try: Log("Summary: " + str(episode.summary))
										except: Log("Summary: -")
										Log("Writers:")
										try: [Log("\t" + writer) for writer in episode.writers]
										except: Log("\t-")
										Log("Directors:")
										try: [Log("\t" + director) for director in episode.directors]
										except: Log("\t-")
										try: Log("Duration: " + str(episode.duration // 60000) + ' min')
										except: Log("Duration: -")
										Log("---------------------")
									else:
										Log("ERROR: <episodedetails> tag not found in episode NFO file " + nfoFile)

		# Final Steps
		duration_min = 0
		duration_string = ""
		if not metadata.duration:
			try:
				duration_min = Dict[duration_key].index(max(Dict[duration_key]))
				for d in Dict[duration_key]:
					if (d != 0):
						duration_string = duration_string + "(" + str(Dict[duration_key].index(d)) + "min:" + str(d) + ")"
			except:
				self.DLog("Error accessing duration_key in dictionary!")
				pass
			self.DLog("Episode durations are: " + duration_string)
			metadata.duration = duration_min * 60 * 1000
			self.DLog("Set Series Episode Runtime to median of all episodes: " + str(metadata.duration) + " (" + str (duration_min) + " minutes)")
		else:
			self.DLog("Series Episode Runtime already set! Current value is:" + str(metadata.duration))
		Dict.Reset()
