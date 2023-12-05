from chdb import session as chs
import streamlit as st

st.title("Mid Journey Images")

sess = chs.Session('../aiven.chdb')

image_count = sess.query("from MidJourney.images select formatReadableQuantity(count())", 'LineAsString')

st.markdown("## Total images")
st.markdown(image_count)

st.markdown("## Largest Image")
large_images = sess.query("""
SELECT
    max(size),
    argMax(width, size),
    argMax(height, size)
FROM MidJourney.images
""", 'DataFrame')
st.dataframe(large_images)

st.markdown("## Smallest Image")
large_images = sess.query("""
SELECT
    min(size),
    argMin(width, size),
    argMin(height, size)
FROM MidJourney.images
""", 'DataFrame')
st.dataframe(large_images)

st.markdown("## Sizes over time")
large_images = sess.query("""
from MidJourney.images 
select toString(toStartOfMonth(timestamp)) AS ts, max(size), min(size) 
GROUP BY ALL 
ORDER BY ts
""", 'DataFrame')
st.dataframe(large_images)
