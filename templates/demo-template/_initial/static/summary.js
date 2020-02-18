$( function () {
	var navMap = {};
	$( '.nav-contest a, .nav-group-header a' )
		.each ( function () {
			var href = $( this ).attr( 'href' );
			if ( href.charAt( 0 ) !== '#' ) {
				return;
			}
			navMap[ href.slice( 1 ) ] = this;
		} );

	function setCurrentFromHash() {
		var matchingNav = navMap[ location.hash.slice( 1 ) ];
		$( '.nav-current' ).removeClass( 'nav-current' );
		if ( matchingNav ) {
			$( matchingNav ).addClass( 'nav-current' );
			matchingNav.scrollIntoView( { block: 'nearest' } );
		}
	}

	$( window ).on( 'hashchange', setCurrentFromHash );
	setCurrentFromHash();

	$( '.main-wrapper' ).on( 'scroll', function () {
		var $firstVisible, $currentHeader, matchingNav,
			$current = $( '.nav-current' );

		if ( $( '.content-wrapper' ).offset().top >= 0 ) {
			return;
		}

		// Find the first element that is at least partially visible
		$( '.content-wrapper' ).children().each( function () {
			if ( $( this ).offset().top + $( this ).height() >= 0 ) {
				$firstVisible = $( this );
				return false;
			}
		} );
		// If $firstVisble is a header, use it; otherwise find the first header above it
		$currentHeader = $firstVisible.is( 'h2, h3, .contest' ) ?
			$firstVisible : $firstVisible.prevAll( 'h2, h3, .contest' ).last();
		if ( $currentHeader.hasClass( 'contest' ) ) {
			$currentHeader = $currentHeader.children( 'h3' );
		}

		// Find the navigation item pointing to this header's ID, and highlight it
		matchingNav = navMap[ $currentHeader.attr( 'id' ) ];
		if ( matchingNav !== $current[ 0 ] ) {
			$current.removeClass( 'nav-current' );
			if ( matchingNav ) {
				$( matchingNav ).addClass( 'nav-current' );
				matchingNav.scrollIntoView( { block: 'nearest' } );
			}
		}
	} );

	$( '.question-text a' ).on( 'click', function () {
		$( this ).closest( '.question-text' ).toggleClass( 'expanded' );
		return false;
	} );
} );
