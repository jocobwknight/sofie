# SoFiE

## The mission
Splunk Functionality Extensions! This humble-beginnings project seeks to pull out the untapped potential that Splunk has.

## The vision
Anyone familiar with setting up a web-server should have a deep admiration for one of Splunk's lesser known features. Namely, Splunk is a packaged, out-of-the-box web-server that also just _happens_ to have an amazing data analytics engine. You can set up any webpage you want, customize the REST API, and schedule tasks on day-1 at enterprise scale. Not to mention (but I'll mention), it has built-in security and user management with an array of LDAP integrations. In a nutshell, it's weeks/months of server development done in advance, written in low level language, and extended with high level scripts.

But Splunk just gives this all out as a footnote to its main offering! Big data is the sell, and they sell well. Sofie, on the other hand, has a different opinion. The Splunk tech itself is offered free to everyone as long as your data intake is less than 512 MB per day, but that's not 512 MB of network activity or internal logs! The net traffic and app logs are fed into an exempt index, meaning it can be extended without any cost. So why aren't we!? Why don't we make it everything it could be? Isn't it the job of passionate independent developers to polish the gems we find? Sofie is with for you. Aren't you for Sofie?

## The plan
Splunk needs several key extensions to make it a fully functional utility for all use cases:
- SPL needs to be extended to operate like a true programming language
- SPL also needs to perform successive REST API transactions
- Splunk's Password API needs to be bridged to its query system
- Splunk's REST API mapping should be extended to be used as a public splash page and non-user activities
- The XML dashboard system needs a utility to build and insert SVG diagrams (think draw.io)
- The HTML dashboard system needs templating
- An HTML editor needs to be built separate from the current system (a UI, not a textbox)
- The new HTML editor also needs to be able to save as an email alert template
- Conf files need to be accessible through the WebUI
- An IDE for creating, testing, and installing extension scripts
- Image file uploads through the WebUI (possibly other binaries)

These may seem like an odd assortment, but they're the ones I've encountered use cases for so far. Many of them have been pioneered somewhat by other projects, and my teammates and I have made headway in others. (Some though have zero progress)

Splunk has an easy system for installing add-ons. The directory structure of this project gets installed into $SPLUNK_HOME/etc/apps, and it will be seen as a internal app (provided it has the right conf files and Splunk gets restarted). Once installed, an app is a dedicated URL extension in the main WebUI, meaning that all these utilities would be instantly available to any Splunk User that installs Sofie. The the plan is the build out all these functionality extensions and package them in a single Splunk Add-On. Then, any Sofie install will transform Splunk into a Web Server Development Framework that can be used for monitoring, automating, hosting, analyzing, etc-ering.

## Installation

Eventually the goal is to get this on Splunkbase, but until then just clone this into $SPLUNK_HOME/etc/apps

```bash
git clone https://github.com/jocobwknight/sofie.git
```

## Usage
Installing and restarting Splunk should add extra features globally to Splunk. It will add new utilities in the form of linked webpages under the sofie app, as well as optional SPL commands, alert actions, and possibly visualizations.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. I'm a full time developer with several volunteer duties outside of work hours, so I apologize in advance if my responsiveness is unsatisfactory.

Please make sure to update tests as appropriate.

## License
[unlicense](https://unlicense.org)
