class User:
    """
    Represents a roblox user.
    """
    def __init__(self, request, roblox_id, roblox_name):
        """
        Construct a new user class.
        :param request: Used for sending requests
        :param roblox_id: the id of the roblox user
        :param roblox_name: the name of the roblox user
        """
        self.request = request
        self.id = roblox_id
        self.name = roblox_name