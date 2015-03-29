# FileViewer::Plugin.pm by mh 2005-2007
#
# This code is derived from code with the following copyright message:
#
# SliMP3 Server Copyright (C) 2001 Sean Adams, Slim Devices Inc.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License,
# version 2.
#
# Changelog
# 1.5 - SqueezeCenter 7.0 compatibility
# 1.0 - initial release

use strict;

package Plugins::XSqueezeDisplay::Plugin;
use base qw(Slim::Plugin::Base);

use vars qw($VERSION);
use Plugins::XSqueezeDisplay::Settings;
use Slim::Utils::Strings qw (string);
use Slim::Utils::Prefs;
use Slim::Utils::Log;
use Time::Seconds;
use LWP::UserAgent;
use JSON;

my $ua = LWP::UserAgent->new;

my $log = Slim::Utils::Log->addLogCategory({
	'category'     => 'plugin.xsqueezedisplay',
	'defaultLevel' => 'INFO',
	'description'  => getDisplayName(),
});


my $prefs = preferences('plugin.xsqueezedisplay');

my ($delay, $lines, $server_endpoint, $state, $timeRemaining);

sub getDisplayName { return 'PLUGIN_XSQUEEZEDISPLAY'; }

sub initPlugin {
	my $class = shift;
	$class->SUPER::initPlugin(shift);

	$VERSION = $class->_pluginDataFor('version');

	Plugins::FileViewer::Settings->new;

	Slim::Buttons::Common::addSaver( 'SCREENSAVER.xsqueezedisplay',
		getFunctions(), \&setScreenSaverMode,
		undef, getDisplayName() );

	# $delay = $prefs->get('plugin_fileviewer_updateinterval') + 1;
	$delay = 1;
	$server_endpoint = join('', 'http://', $prefs->get('plugin_xsqueezedisplay_kodiip'),':',$prefs->get('plugin_xsqueezedisplay_kodijsonport'), '/jsonrpc');
	myDebug(join("","Server endpoint is ", $server_endpoint));
	$state = "Stopped";
	$timeRemaining = "";
}

sub setMode {
	my $class  = shift;
	my $client = shift;
	my $method = shift;

	if ($method eq 'pop') {
		Slim::Buttons::Common::popMode($client);
		return;
	}

	my $lines = _readFile($client);

	my %params = (
		stringHeader => 1,
		header => 'PLUGIN_XSQUEEZEDISPLAY',
		headerAddCount => 1,
		listRef => $lines,
		parentMode => Slim::Buttons::Common::mode($client),		  
	);

	Slim::Buttons::Common::pushMode($client, 'INPUT.List', \%params);
}

my %xSqueezeDisplayFunctions = (
	'done' => sub {
		my ( $client, $funct, $functarg ) = @_;
		Slim::Buttons::Common::popMode($client);
		$client->update();

		# pass along ir code to new mode if requested
		if ( defined $functarg && $functarg eq 'passback' ) {
			Slim::Hardware::IR::resendButton($client);
		}
	}
);

sub getFunctions {
	return \%xSqueezeDisplayFunctions;
}

sub setScreenSaverMode {
	my $client = shift;
	$client->modeParam('modeUpdateInterval', 1);
	$client->lines(\&screensaverXSqueezeDisplayLines);
}

sub sec2human {
    my $secs = shift;
    if    ($secs >= 365*24*60*60) { return sprintf '%.1fy', $secs/(365*24*60*60) }
    elsif ($secs >=     24*60*60) { return sprintf '%.1fd', $secs/(    24*60*60) }
    elsif ($secs >=        60*60) { return sprintf '%.1fh', $secs/(       60*60) }
    elsif ($secs >=           60) { return sprintf '%.1fm', $secs/(          60) }
    else                          { return sprintf '%.1fs', $secs                }
}

sub kodiJSON {
		my $post_data = shift;

		#assemble the JSON POST request
		my $req = HTTP::Request->new(POST => $server_endpoint);
		$req->header('content-type' => 'application/json');
		$req->content($post_data);

		#myDebug(join("", "JSON Request to: 	",$server_endpoint));
		#myDebug(join("", "JSON Request is: 	", $post_data));

		# submit the request
		my $resp = $ua->request($req);

		#  YAY! 
		if ($resp->is_success) {
		    #my $message = $resp->decoded_content;
		    #myDebug("JSON Request Success: $message\n");
		    return $resp;
		}
		#oh dear....
		else {
		    myDebug(join("JSON Request error code: 		", $resp->code, "\n"));
		    myDebug(join("JSON Request error message: 	", $resp->message, "\n"));
			return $resp;
		}	
	    
	    
}

sub screensaverXSqueezeDisplayLines {

	my $client = shift;

	$lines = join(' ', @{_readFile($client)});

	# initial hack in of JSON request to XBMC
	my $req = HTTP::Request->new(POST => $server_endpoint);
	$req->header('content-type' => 'application/json');

	#debug - introspect test the kodi json API here
	# my $post_data = '{ "jsonrpc": "2.0", "method": "JSONRPC.Introspect", "params": { "filter": { "id": "Player.GetItem", "type": "method" } }, "id": 1 }';

	# Get the active players

	my $post_data = '{
		"jsonrpc": "2.0", 
		"method": "Player.GetActivePlayers", 
		"id": 1
		}';

	my $resp = kodiJSON($post_data);

	if ($resp->is_success) {
		my $message = decode_json $resp->decoded_content;
		if (@{$message->{result}}){
	    	myDebug(join("|","Player(s) Active...",@{$message->{result}},"]"));
	    	$state = "Playing";


			# Get the play progress time
			my $post_data = '{
			    "jsonrpc": "2.0",
			    "method": "Player.GetProperties",
			    "params": {
			        "properties": [
			            "percentage",
			            "time",
			            "totaltime"
			        ],
			        "playerid": 1
			    },
			    "id": 1
			}';

			$resp = kodiJSON($post_data);
			$message = decode_json $resp->decoded_content;

			my $duration = ($message->{'result'}{'totaltime'}{'minutes'} * 60) + $message->{'result'}{'totaltime'}{'seconds'};
			my $elapsed = ($message->{'result'}{'time'}{'minutes'} * 60) + $message->{'result'}{'time'}{'seconds'};
			my $difference = $duration - $elapsed;
			my $hours = ($difference/(60*60))%24;
			my $minutes = ($difference/60)%60;
			my $seconds = $difference%60;
			myDebug("Hours " . $hours . " Minutes " . $minutes . " Seconds " . $seconds);
			$timeRemaining = "-" . join(":",$hours,$minutes,$seconds)

		}
	    else {
			myDebug("Players NOT Active...");
			$state = "Inactive"
	    }
	} 



	return {
		'line1' => $state,
		'line2' => $timeRemaining
	};
}

sub _readFile {
	my $client = shift;
	my @lines;

	if (open MYFILE, $prefs->get('plugin_fileviewer_filename')) {
		@lines = <MYFILE>;
		close MYFILE;
	}
	else {
		push @lines, 'TEST2';
	}	

	return \@lines;
}

sub myDebug {
	my $msg = shift;
	my $lvl = shift;
	
	if ($lvl eq "")
	{
		$lvl = "debug";
	}
	
	$log->$lvl("*** XSqueezeDisplay *** $msg");
}



				# Get the data about the now playing item
				# my $post_data = '{
				#     "jsonrpc": "2.0",
				#     "method": "Player.GetItem",
				#     "params": {
				#         "properties": [
				#             "title",
				#             "album",
				#             "artist",
				#             "season",
				#             "episode",
				#             "duration",
				#             "showtitle",
				#             "tvshowid",
				#             "thumbnail",
				#             "file",
				#             "fanart",
				#             "streamdetails",
				#             "resume"
				#         ],
				#         "playerid": 1
				#     },
				#     "id": "VideoGetItem"
				# }';

				# my $resp = kodiJSON($post_data);




1;
