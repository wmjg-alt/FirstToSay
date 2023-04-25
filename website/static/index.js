function like(postId){
    const likeCount = document.getElementById(`likes-count-${postId}`);
    const likeButton = document.getElementById(`likes-button-${postId}`);
    
    fetch(`/like-quote/${postId}`, { method: 'POST' })
        .then((res) => res.json())
        .then((data) => {
            likeCount.innerHTML = data['likes'];
            if(data['liked']){
                likeButton.className = "fas fa-heart fa-xl";
                likeButton.style = style="color: red;";
            } else{
                likeButton.className = "far fa-heart fa-xl";
                likeButton.style = style="color: grey;";
            }
        }).catch((e) => alert("couldn't like post, something failed"));
    
    
}