
(function(global) {
  'use strict'

  var usercontrol = {};
  var me = this;

  usercontrol.start = function() {
    console.log("start method called.");
    console.log(global.gapi);
    global.gapi.load('auth2', function() {
      usercontrol.auth2 = global.gapi.auth2.init({
        client_id: '645762832040-gcp2qd1fkgta26c3218l8c43roqsvrnk.apps.googleusercontent.com',
        // Scopes to request in addition to 'profile' and 'email'
        //scope: 'additional_scope'
      });
    });
  };

  usercontrol.signIn = function(){
    console.log(me)
    console.log(usercontrol)

    // usercontrol.auth2.grantOfflineAccess({'redirect_uri': 'postmessage'}).then(usercontrol.signInCallback);
     usercontrol.auth2.signIn().then(usercontrol.signInCallback);
  };
  usercontrol.signInCallback = function(googleUser){
    console.log("got user");
    console.log(googleUser);

    var profile = googleUser.getBasicProfile();
    console.log("profile:");
    console.log(profile);

    var id_token = googleUser.getAuthResponse().id_token;
    console.log("id_token");
    console.log(id_token);

    if (id_token) {
      // Send the code to the server
      $.ajax({
        type: 'POST',
        url: 'user/login',
        success: function(result) {
          // Handle or verify the server response.
          console.log("ajax result")
          console.log(result)
          if (result.redirect)
            global.location = result.redirect
        },
        data: {'id_token': id_token}
      });
    } else {
      // There was an error.
      console.log("auth error.")
    }
  };

usercontrol.onSignIn = function(googleUser) {
    var profile = googleUser.getBasicProfile();
    console.log(profile)
    console.log('ID: ' + profile.getId()); // Do not send to your backend! Use an ID token instead.
    console.log('Name: ' + profile.getName());
    console.log('Image URL: ' + profile.getImageUrl());
    console.log('Email: ' + profile.getEmail());
  };


  usercontrol.signOut = function() {

    usercontrol.auth2.signOut().then(function () {
      console.log('User signed out.');
      global.location="user/logout"
    });
  };

  global.usercontrol = usercontrol;

})(window);

$(function () { // Same as document.addEventListener("DOMContentLoaded"...
  usercontrol.start();
});
