import PyBoardObjects

# The extension's main class must be called 'main', and it must subclass PyBoardObjects.Extension.
class main(PyBoardObjects.Extension):
    """
    This is an example extension which shows usage for most API methods.
    It will hopefully be updated as the API is changed.
    """
    # The name your extension is known by internally. Allowed chars: [A-Z, a-z, .]
    IDENTIFIER = "net.pyboard.exampleExtension"
    # These two flags allow your extension to have a place for general storage
    # and a configuration file.
    REQUIRES_DATA_FOLDER = True # Accessible through self.dataFolder
    # if REQUIRES_CONFIG_FILE is True, then REQUIRES_DATA_FOLDER is also implicitly True.
    REQUIRES_CONFIG_FILE = False # Accessible through self.config or self.getConfig()
    def __init__(self, PyBoard):
        super(main, self).__init__(PyBoard)
        self.addPage("/example/res_file", self.demoResponseFromFile)
        self.addPage("/example/echo_method", self.echoMethod)
        self.addPage("/example/redirect", self.demoRedirect)
        self.addPage("/example/error", self.demoError)
        self.addPage("/example/broken", self.brokenHandler)
        self.addModView("h", "h h", self.modViewDemo)
        self.hook("PBApplicationLady", self.eventHook)

    # Page handlers can be either functions or classes (see echoMethod below) and must return a Response object.
    def demoResponseFromFile(self, request): # Page handlers take one argument: a Request object.
        """
        This page handler serves a file from the data folder using the responseFromFile API method.
        """
        return self.responseFromFile("{0}/h.png".format(self.dataFolder), status="200 OK", headers={
            "Content-Disposition": "inline; filename=h.png"
        })

    # Page handler classes must subclass PyBoardObjects.Extension.RequestHandler.
    class echoMethod(PyBoardObjects.Extension.RequestHandler):
        # and they can implement any/all of the get, post, head methods...
        def get(self, request):
            # ...which take the same arguments as handler functions.
            return PyBoardObjects.Response(s="200 OK", h={
                "Content-Type": "text/plain",
                # The Content-Length header will automatically be filled in by the constructor.
                # But you might have to fix it yourself if you replace rdata after creating the response object.
            }, r="This is a GET request!")

        def post(self, request):
            return PyBoardObjects.Response(s="200 OK", h={
                "Content-Type": "text/plain",
            }, r="This is a POST request!")

        def head(self, request):
            return PyBoardObjects.Response(s="200 OK", h={
                "X-Content": "This is a HEAD request!",
            }, r="")

    def modViewDemo(self, request):
        """
        Mod views are accessed from the mod panel's sidebar. They are just like page handlers, but should return only an HTML fragment, not a response.
        """
        return "<a href=\"/admin\"><img class=\"test\" src=\"/example/res_file\"></a><br><br>Hello world! :)<br>{0}".format(repr(self).replace("<", "&lt;").replace(">", "&gt;"))

    def demoRedirect(self, request):
        """
        This page handler redirects visitors to the home page.
        """
        return self.redirect("/")

    def demoError(self, request):
        """
        This page handler returns a uniform error page.
        """
        return self.generateError(status="418 I'm a teapot", heading="Oops", return_to="/", etext="I was wrong. There is no error here.")

    def eventHook(self, event):
        """
        You can also listen for events...
        """
        self.log("Look! It's a {0}Event!".format(event.name))
        self.log("Warning! It's a {0}Event!".format(event.name), self.LOGLEV_WARN)
        self.log("Error! It's a {0}Event!".format(event.name), self.LOGLEV_ERROR)

    def brokenHandler(self, request):
        """
        PyBoard will automatically serve error pages for broken handlers...
        """
        try:
            a = 12 / 0 # Oops!
        except ZeroDivisionError:
            a = 0 # It's okay, we catch the error.
        return PyBoardObjects.Response(s="200 OK", h={
            "Content-Type": "text/plain",
        }, r=str(b)) # b isn't defined
