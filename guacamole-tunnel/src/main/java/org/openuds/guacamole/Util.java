package org.openuds.guacamole;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.Hashtable;

public class Util {
	
	//
	public static Hashtable<String,String> readParameters(String url) {
		//String url = unscramble(data);
		//String params = getUrl(url);
		//return parseParams(params);
		//String params = Credentials.getAndRemove(data);
		String params = getUrl(url);
		if( params == null || params.equals("ERROR"))
			return null;
		return parseParams(params);
	}
	
	public static Hashtable<String,String> parseParams(String params)
	{
		Hashtable<String,String> res = new Hashtable<String, String>();
		String[] parms = params.split("\n");
		for( int i = 0; i < parms.length;  i++) {
			String[] val = parms[i].split("\t");
			if( val.length == 1 )
				res.put(val[0], "");
			else
				res.put(val[0], val[1]);
		}
		return res;
	}
	
	
	public static boolean download(String baseUrl, String id, String outputFileName)
	{
		try {
			java.net.URL u = new java.net.URL(baseUrl + id);
			java.net.URLConnection uc = u.openConnection();
		    String contentType = uc.getContentType();
		    int contentLength = uc.getContentLength();
		    if (contentType.startsWith("text/") || contentLength == -1) {
		      throw new IOException("This is not a binary file.");
		    }
		    InputStream raw = uc.getInputStream();
		    InputStream in = new BufferedInputStream(raw);
		    byte[] data = new byte[contentLength];
		    int bytesRead = 0;
		    int offset = 0;
		    while (offset < contentLength) {
		      bytesRead = in.read(data, offset, data.length - offset);
		      if (bytesRead == -1)
		        break;
		      offset += bytesRead;
		    }
		    in.close();

		    if (offset != contentLength) {
		      throw new IOException("Only read " + offset + " bytes; Expected " + contentLength + " bytes");
		    }		    
		    
			java.io.FileOutputStream out = new java.io.FileOutputStream(outputFileName);
		    out.write(data);
		    out.flush();
		    out.close();			
			
		} catch(Exception e) {
			System.out.println("Unable to download file, already present or network error? " + e.getMessage());
			return false;
		}
		return true;
	}
	
	
	public static String getUrl(String url) {
		try {
			java.net.URL u = new java.net.URL(url);
			BufferedReader in = new BufferedReader(new InputStreamReader(u.openStream()));
			StringBuilder data = new StringBuilder();
			
			String inputLine;
			while ((inputLine = in.readLine()) != null) {
				data.append(inputLine);
				data.append("\n");
			}
				
			in.close();
			return data.toString();
			
		} catch(Exception e) {
			System.out.println("Unable to get url. Network error? " + e.getMessage());
			return null;
		}
		
	}
	
}