$(document).ready(function() {

    // Create a Stripe client.
    if (location.protocol === 'https:') {
      var stripe = Stripe('pk_live_MHlS4I7NN4fGQKiR3JUfSMnZ');
    } else {
      var stripe = Stripe('pk_test_4QJqyITTSyRkqahvU1EQ3idM');
    }

  // Create an instance of Elements.
  var elements = stripe.elements();

  // Custom styling can be passed to options when creating an Element.
  // (Note that this demo uses a wider set of styles than the guide below.)
  var style = {
    base: {
      color: '#32325d',
      fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
      fontSmoothing: 'antialiased',
      fontSize: '16px',
      '::placeholder': {
        color: '#606060'
      }
    },
    invalid: {
      color: '#fa755a',
      iconColor: '#fa755a'
    }
  };

  // Create an instance of the card Element.
  var card = elements.create('card', {style: style, hidePostalCode: false});

  // Add an instance of the card Element into the `card-element` <div>.
  card.mount('#card-element');

  // Handle real-time validation errors from the card Element.
  card.addEventListener('change', function(event) {
    var displayError = document.getElementById('card-errors');
    if (event.error) {
      displayError.textContent = event.error.message;
    } else {
      displayError.textContent = '';
    }
  });

  // Payment - Handle form submission.
  var form = document.getElementById('payment-form');
  if (form != null) {
    form.addEventListener("submit", function(event) {
      event.preventDefault();
      stripe.confirmCardPayment(clientSecret, {payment_method: {card: card}}).then(
          function(result) {
            if (result.paymentIntent.status === 'succeeded') {
              $.getJSON($SCRIPT_ROOT + '/_clear_cart', {}, function(data) {
                location.href = successRedirectUrl;
              });
            } else {
              location.href = errorRedirectUrl;
            }
          }
      )
    });
  } else {
    // Add card - Handle form submission.
    var form = document.getElementById('add-card-form');
    form.addEventListener("submit", function(event) {
      var cardholderName = document.getElementById('cardholder-name');
      var cardButton = document.getElementById('card-button');
      var clientSecret = cardButton.dataset.secret;
      event.preventDefault();
      stripe.confirmCardSetup(
        clientSecret,
        {
          payment_method: {
            card: card,
            billing_details: {name: cardholderName.value}
          }
        }
      ).then(function(result) {
        if (result.error) {
          location.href = errorCardAddUrl + '/' + 'error';
        } else {
          location.href = successCardAddUrl + '/' + result.setupIntent.payment_method;
        }
      });
    });
  }

  // Submit the form with the token ID.
  function stripeTokenHandler(token) {
    // Insert the token ID into the form so it gets submitted to the server
    var form = document.getElementById('payment-form');
    var hiddenInput = document.createElement('input');
    hiddenInput.setAttribute('type', 'hidden');
    hiddenInput.setAttribute('name', 'stripeToken');
    hiddenInput.setAttribute('value', token.id);
    form.appendChild(hiddenInput);

    // Submit the form
    form.submit();
  }

});
